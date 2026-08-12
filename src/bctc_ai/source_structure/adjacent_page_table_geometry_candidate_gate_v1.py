"""Apply one frozen blind exploratory seed envelope to adjacent-page geometry.

This add-only gate composes the exact adjacent-page geometry builder with a
fixed, integer-only candidate-search policy.  The policy values are the eight
inclusive marginal p25 measurements retained from the blind full-Wave-1
Cartesian assay.  They are reduction/search references, not labels,
calibration, confidence, accuracy, or a continuation decision.

Every upstream relation, Cartesian axis distance, fragment, physical axis and
page pair receives exactly one disposition.  Passing evidence remains a seed
candidate.  Failing, ambiguous, terminal and counterpart-free evidence remains
explicitly unresolved; it is never promoted to a negative or absence claim.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Any

from bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1 import (
    ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1,
    ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1,
    build_adjacent_page_table_geometry_relations_v1,
)
from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
    same_typed_json_v1,
)

__all__ = [
    "ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_CLAIM_BOUNDARY_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_FORMAT_VERSION_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1",
    "ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_STATUS_V1",
    "LOWER_QUARTILE_MARGINAL_ENVELOPE_V1",
    "AdjacentPageTableGeometryCandidateGateError",
    "build_adjacent_page_table_geometry_candidate_gate_v1",
    "validate_adjacent_page_table_geometry_candidate_gate_v1",
]


class AdjacentPageTableGeometryCandidateGateError(ValueError):
    """Authenticated adjacent-page geometry cannot form the closed seed gate."""


ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_FORMAT_VERSION_V1 = (
    "BANK_CORPUS_WAVE_1_ROLE_B_ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_V1"
)
ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_CLAIM_BOUNDARY_V1 = (
    "BLIND_EXPLORATORY_GEOMETRY_SEED_CANDIDATES_AND_COMPLETE_UNRESOLVED_"
    "DISPOSITIONS_ONLY_NO_WINNER_SAME_TABLE_SUCCESSOR_CONTINUATION_MERGE_"
    "OWNERSHIP_SEMANTIC_CALIBRATION_ACCURACY_OR_ABSENCE_CLAIM"
)
ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_STATUS_V1 = (
    "COMPLETE_ADJACENT_PAGE_EXPLORATORY_GEOMETRY_SEED_ACCOUNTING"
)

_UPSTREAM_MODULE_SHA256 = "63763fa9a4bb91f797b55b2e50c687a2aeb47748476040b974fdafc8640f0013"
_UPSTREAM_TEST_SHA256 = "3cc6db4c316837ddfcef368325715e6ab36af1c758220a93f4109fb518e87424"
_MEASUREMENT_RECEIPT_SHA256 = "4f8f9e1672d3a1672a2e4a3bcc959922b4eb65b58ad6b987467b67cf17864c13"
_MEASUREMENT_RECEIPT_SIZE_BYTES = 24_162
_MEASUREMENT_RECEIPT_STATUS = (
    "PASS_EXHAUSTIVE_READ_ONLY_ADJACENT_PAGE_RELATION_SUMMARY_RECOVERY_OPTIMIZED_V1"
)
_MEASUREMENT_CLEAN_GIT_COMMIT = "4d1506a24f4e180023b58689ea4cd770db0f0fde"
_MEASUREMENT_PHASE_CLOSE_GIT_COMMIT = "f05bc37062530fbcd49d56d329fc656e82b5b3b1"

_TABLE_LEFT_CAP = 1_236
_TABLE_RIGHT_CAP = 1_854
_TABLE_WIDTH_CAP = 2_473
_PREVIOUS_BOTTOM_CAP = 94_587
_FOLLOWING_TOP_CAP = 45_299
_AXIS_X0_CAP = 53_505
_AXIS_X2_CAP = 53_011
_AXIS_CENTER2_CAP = 106_492
_MINIMUM_SINGLETON_LINKS = 2

_TABLE_CHECK_FIELDS = (
    "left_edge_within_cap",
    "right_edge_within_cap",
    "width_within_cap",
)
_BOUNDARY_CHECK_FIELDS = (
    "previous_bottom_within_cap",
    "following_top_within_cap",
)
_AXIS_CHECK_FIELDS = (
    "x0_within_cap",
    "x2_within_cap",
    "doubled_center2_within_cap",
)
_RELATION_FAILURE_FIELDS = (
    "table_left_edge_outside_envelope",
    "table_right_edge_outside_envelope",
    "table_width_outside_envelope",
    "previous_bottom_outside_envelope",
    "following_top_outside_envelope",
    "fewer_than_two_bidirectionally_singleton_axis_links",
)
_RELATION_FAILURE_CODES = {
    "table_left_edge_outside_envelope": "TABLE_LEFT_EDGE_OUTSIDE_EXPLORATORY_ENVELOPE",
    "table_right_edge_outside_envelope": "TABLE_RIGHT_EDGE_OUTSIDE_EXPLORATORY_ENVELOPE",
    "table_width_outside_envelope": "TABLE_WIDTH_OUTSIDE_EXPLORATORY_ENVELOPE",
    "previous_bottom_outside_envelope": "PREVIOUS_FRAGMENT_NOT_NEAR_ENOUGH_PAGE_BOTTOM",
    "following_top_outside_envelope": "FOLLOWING_FRAGMENT_NOT_NEAR_ENOUGH_PAGE_TOP",
    "fewer_than_two_bidirectionally_singleton_axis_links": (
        "FEWER_THAN_TWO_BIDIRECTIONALLY_SINGLETON_AXIS_GEOMETRY_LINKS"
    ),
}

_RELATION_OUTSIDE = "RETAINED_OUTSIDE_TABLE_OR_PAGE_ENVELOPE_UNRESOLVED"
_RELATION_AXIS_INSUFFICIENT = (
    "RETAINED_WITH_INSUFFICIENT_BIDIRECTIONALLY_SINGLETON_AXIS_SUPPORT_UNRESOLVED"
)
_RELATION_SEED = "GEOMETRY_SUPPORTED_EXPLORATORY_SEED_CANDIDATE"
_RELATION_DISPOSITIONS = (
    _RELATION_OUTSIDE,
    _RELATION_AXIS_INSUFFICIENT,
    _RELATION_SEED,
)

_DISTANCE_OUTSIDE = "RETAINED_OUTSIDE_AXIS_ENVELOPE_UNRESOLVED"
_DISTANCE_AMBIGUOUS = "WITHIN_AXIS_ENVELOPE_AMBIGUOUS_SEED_LINK"
_DISTANCE_SINGLETON = "WITHIN_AXIS_ENVELOPE_BIDIRECTIONALLY_SINGLETON_SEED_LINK"
_DISTANCE_DISPOSITIONS = (
    _DISTANCE_OUTSIDE,
    _DISTANCE_AMBIGUOUS,
    _DISTANCE_SINGLETON,
)

_FRAGMENT_UPSTREAM_RETAINED = "UPSTREAM_RETAINED_WITHOUT_MEASURED_COUNTERPART_UNRESOLVED"
_FRAGMENT_ZERO = "RETAINED_WITH_ZERO_GEOMETRY_SUPPORTED_RELATIONS_UNRESOLVED"
_FRAGMENT_RECIPROCAL = "ONE_RECIPROCAL_SINGLETON_FRAGMENT_SEED_CANDIDATE"
_FRAGMENT_ONE_SIDED = "ONE_NONRECIPROCAL_FRAGMENT_SEED_AMBIGUOUS_UNRESOLVED"
_FRAGMENT_MULTIPLE = "MULTIPLE_FRAGMENT_SEEDS_AMBIGUOUS_UNRESOLVED"
_FRAGMENT_DISPOSITIONS = (
    _FRAGMENT_UPSTREAM_RETAINED,
    _FRAGMENT_ZERO,
    _FRAGMENT_RECIPROCAL,
    _FRAGMENT_ONE_SIDED,
    _FRAGMENT_MULTIPLE,
)

_AXIS_UPSTREAM_RETAINED = "UPSTREAM_RETAINED_WITHOUT_AXIS_COUNTERPART_UNRESOLVED"
_AXIS_ZERO = "RETAINED_WITH_ZERO_AXIS_ENVELOPE_LINKS_UNRESOLVED"
_AXIS_AMBIGUOUS_ONLY = "RETAINED_WITH_ONLY_AMBIGUOUS_AXIS_ENVELOPE_LINKS_UNRESOLVED"
_AXIS_ONE_SINGLETON = "ONE_BIDIRECTIONALLY_SINGLETON_AXIS_SEED_CANDIDATE"
_AXIS_MIXED = "MULTIPLE_OR_MIXED_AXIS_SEED_LINKS_AMBIGUOUS_UNRESOLVED"
_AXIS_DISPOSITIONS = (
    _AXIS_UPSTREAM_RETAINED,
    _AXIS_ZERO,
    _AXIS_AMBIGUOUS_ONLY,
    _AXIS_ONE_SINGLETON,
    _AXIS_MIXED,
)

_UPSTREAM_MEASURED_PAIR = "MEASURED_CARTESIAN_FRAGMENT_PAIRS"
_UPSTREAM_MEASURED_FRAGMENT = "MEASURED_IN_CARTESIAN_FRAGMENT_PAIRS"
_UPSTREAM_MEASURED_AXIS = "MEASURED_IN_CARTESIAN_AXIS_PAIRS"
_PAIR_NO_SEED = "NO_GEOMETRY_SUPPORTED_EXPLORATORY_SEED_UNRESOLVED"
_PAIR_RECIPROCAL = "ONE_OR_MORE_RECIPROCAL_SINGLETON_GEOMETRY_SEEDS_RETAINED"
_PAIR_AMBIGUOUS = "GEOMETRY_SEEDS_WITH_FRAGMENT_AMBIGUITY_RETAINED"
_PAIR_UPSTREAM_RETAINED = "UPSTREAM_NONMEASURED_PAGE_PAIR_RETAINED_UNRESOLVED"
_PAIR_DISPOSITIONS = (
    _PAIR_UPSTREAM_RETAINED,
    _PAIR_NO_SEED,
    _PAIR_RECIPROCAL,
    _PAIR_AMBIGUOUS,
)

_UPSTREAM_PAIR_DISPOSITIONS = (
    "MEASURED_CARTESIAN_FRAGMENT_PAIRS",
    "NO_PREVIOUS_TABLE_CANDIDATE",
    "NO_FOLLOWING_TABLE_CANDIDATE",
    "NO_TABLE_CANDIDATES",
    "UPSTREAM_TERMINAL_BARRIER",
)


LOWER_QUARTILE_MARGINAL_ENVELOPE_V1: dict[str, Any] = {
    "policy_name": "LOWER_QUARTILE_MARGINAL_ENVELOPE_V1",
    "policy_version": 1,
    "policy_role": "BLIND_EXPLORATORY_CANDIDATE_SEARCH_AND_REDUCTION_ENVELOPE",
    "frozen_versioned_policy": True,
    "runtime_measurement_receipt_authority": False,
    "measurement_receipt": {
        "transport": "RETAINED_STDOUT_JSON_ONLY",
        "sha256": _MEASUREMENT_RECEIPT_SHA256,
        "size_bytes": _MEASUREMENT_RECEIPT_SIZE_BYTES,
        "status": _MEASUREMENT_RECEIPT_STATUS,
        "artifact_persisted": False,
        "clean_run_git_commit": _MEASUREMENT_CLEAN_GIT_COMMIT,
        "phase_close_git_commit": _MEASUREMENT_PHASE_CLOSE_GIT_COMMIT,
    },
    "upstream_contract": {
        "module": ("bctc_ai.source_structure.adjacent_page_table_geometry_relations_v1"),
        "module_sha256": _UPSTREAM_MODULE_SHA256,
        "focused_test_sha256": _UPSTREAM_TEST_SHA256,
        "format_version": ADJACENT_PAGE_TABLE_GEOMETRY_FORMAT_VERSION_V1,
        "claim_boundary": ADJACENT_PAGE_TABLE_GEOMETRY_CLAIM_BOUNDARY_V1,
    },
    "percentile_selector": {
        "numerator": 1,
        "denominator": 4,
        "percentile_numerator": 25,
        "percentile_denominator": 100,
        "zero_based_rank_formula": "((sample_count - 1) * numerator) // denominator",
        "selection_formula": ("ordered[((len(ordered) - 1) * numerator) // denominator]"),
        "table_and_page_sample_count": 899,
        "table_and_page_zero_based_rank": 224,
        "axis_sample_count": 122_573,
        "axis_zero_based_rank": 30_643,
    },
    "sample_interpretation": {
        "policy_seed_corpus": "BANK_CORPUS_WAVE_1_ROLE_B_FULL_CARTESIAN_GEOMETRY_ASSAY",
        "same_corpus_gate_replay_is_holdout": False,
        "independent_holdout_used": False,
        "continuation_labels_present": False,
        "policy_tuned_from_role_a": False,
        "role_a_used": False,
        "table_and_page_samples": (
            "RELATION_OCCURRENCE_WEIGHTED_WITH_PAGE_EDGE_VALUES_REPEATED_ACROSS_"
            "CARTESIAN_TABLE_RELATIONS"
        ),
        "axis_samples": "CARTESIAN_DISTANCE_OCCURRENCE_WEIGHTED_AND_CORRELATED",
        "marginal_conjunction_is_twenty_five_percent_gate": False,
        "positive_class_evidence": False,
        "scientific_calibration": False,
        "precision_or_recall_known": False,
    },
    "table_shape_envelope": {
        "mask_order": list(_TABLE_CHECK_FIELDS),
        "comparison": "INCLUSIVE_INTEGER_LESS_THAN_OR_EQUAL",
        "normalized_left_edge_absolute_distance_ppm_maximum": _TABLE_LEFT_CAP,
        "normalized_right_edge_absolute_distance_ppm_maximum": _TABLE_RIGHT_CAP,
        "normalized_width_absolute_distance_ppm_maximum": _TABLE_WIDTH_CAP,
        "sample_count_each": 899,
        "zero_based_rank_each": 224,
    },
    "page_boundary_envelope": {
        "mask_order": list(_BOUNDARY_CHECK_FIELDS),
        "comparison": "INCLUSIVE_INTEGER_LESS_THAN_OR_EQUAL",
        "previous_distance_to_page_bottom_ppm_maximum": _PREVIOUS_BOTTOM_CAP,
        "following_distance_from_page_top_ppm_maximum": _FOLLOWING_TOP_CAP,
        "sample_count_each": 899,
        "zero_based_rank_each": 224,
    },
    "axis_envelope": {
        "mask_order": list(_AXIS_CHECK_FIELDS),
        "comparison": "INCLUSIVE_INTEGER_LESS_THAN_OR_EQUAL",
        "x0_median_absolute_distance_ppm_maximum": _AXIS_X0_CAP,
        "x2_median_absolute_distance_ppm_maximum": _AXIS_X2_CAP,
        "doubled_center2_median_absolute_distance_ppm_maximum": _AXIS_CENTER2_CAP,
        "doubled_center2_domain_maximum_ppm": 2_000_000,
        "sample_count_each": 122_573,
        "zero_based_rank_each": 30_643,
    },
    "relation_seed_support_rule": {
        "all_table_shape_components_required": True,
        "all_page_boundary_components_required": True,
        "minimum_bidirectionally_singleton_axis_links": _MINIMUM_SINGLETON_LINKS,
        "rule_is_uncalibrated_conservative_mechanism_choice": True,
        "zero_one_or_ambiguous_axis_support_is_negative_claim": False,
    },
    "full_wave_1_upstream_accounting_reference": {
        "page_pair_count": 1_422,
        "page_pair_disposition_counts": {
            "MEASURED_CARTESIAN_FRAGMENT_PAIRS": 676,
            "NO_PREVIOUS_TABLE_CANDIDATE": 135,
            "NO_FOLLOWING_TABLE_CANDIDATE": 143,
            "NO_TABLE_CANDIDATES": 359,
            "UPSTREAM_TERMINAL_BARRIER": 109,
        },
        "fragment_occurrence_count": 1_909,
        "measured_fragment_occurrence_count": 1_521,
        "retained_fragment_occurrence_count": 388,
        "axis_occurrence_count": 18_805,
        "measured_axis_occurrence_count": 16_085,
        "retained_axis_occurrence_count": 2_720,
        "relation_count": 899,
        "axis_distance_count": 122_573,
        "upstream_nonmeasured_page_pair_count": 746,
        "occurrence_ids_globally_unique_claimed": False,
    },
    "identity_hash_scope": (
        "CANONICAL_POLICY_PAYLOAD_EXCLUDING_POLICY_PAYLOAD_SHA256_AND_POLICY_IDENTITY"
    ),
}

_POLICY_SHA256 = canonical_json_sha256_v1(LOWER_QUARTILE_MARGINAL_ENVELOPE_V1)
LOWER_QUARTILE_MARGINAL_ENVELOPE_V1["policy_payload_sha256"] = _POLICY_SHA256
LOWER_QUARTILE_MARGINAL_ENVELOPE_V1["policy_identity"] = f"apgcv1:policy:{_POLICY_SHA256}"


ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1: dict[str, bool] = {
    "blind_source_local_geometry_only": True,
    "inclusive_integer_envelope_applied": True,
    "complete_relation_dispositions": True,
    "complete_axis_distance_dispositions": True,
    "complete_fragment_dispositions": True,
    "complete_physical_axis_dispositions": True,
    "complete_page_pair_disposition": True,
    "outside_envelope_retained_unresolved": True,
    "ambiguity_retained": True,
    "threshold_scientifically_calibrated": False,
    "confidence_claimed": False,
    "accuracy_claimed": False,
    "holdout_claimed": False,
    "generalization_claimed": False,
    "unseen_filing_accuracy_claimed": False,
    "positive_or_negative_class_claimed": False,
    "winner_selected": False,
    "accepted_relation_claimed": False,
    "same_table_claimed": False,
    "successor_claimed": False,
    "continuation_claimed": False,
    "merge_claimed": False,
    "ownership_claimed": False,
    "statement_claimed": False,
    "table_semantic_claimed": False,
    "logical_rows_claimed": False,
    "financial_cells_claimed": False,
    "period_claimed": False,
    "unit_claimed": False,
    "scope_claimed": False,
    "hierarchy_claimed": False,
    "absence_claimed": False,
    "schema_used": False,
    "mapping_used": False,
    "visible_text_used": False,
    "numeric_value_used": False,
    "bank_identity_used_for_routing": False,
    "filename_identity_used_for_routing": False,
    "source_path_used_for_routing": False,
    "note_number_used_for_routing": False,
    "role_a_used_for_routing": False,
    "role_a_used": False,
    "historical_values_used": False,
    "model_or_reader_invoked": False,
    "network_used": False,
    "occurrence_ids_globally_unique_claimed": False,
}

_EXPECTED_POLICY_V1 = canonical_clone_v1(LOWER_QUARTILE_MARGINAL_ENVELOPE_V1)
_EXPECTED_SAFETY_V1 = canonical_clone_v1(ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1)
_SAFETY_PAYLOAD_SHA256 = canonical_json_sha256_v1(_EXPECTED_SAFETY_V1)


def _error(message: str) -> AdjacentPageTableGeometryCandidateGateError:
    return AdjacentPageTableGeometryCandidateGateError(message)


def _content_id(namespace: str, value: Mapping[str, Any]) -> str:
    return f"apgcv1:{namespace}:{canonical_json_sha256_v1(value)}"


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise _error(message)


def _validate_static_contract_integrity() -> None:
    policy_payload = {
        key: value
        for key, value in LOWER_QUARTILE_MARGINAL_ENVELOPE_V1.items()
        if key not in {"policy_payload_sha256", "policy_identity"}
    }
    if (
        canonical_json_sha256_v1(policy_payload) != _POLICY_SHA256
        or LOWER_QUARTILE_MARGINAL_ENVELOPE_V1.get("policy_payload_sha256") != _POLICY_SHA256
        or LOWER_QUARTILE_MARGINAL_ENVELOPE_V1.get("policy_identity")
        != f"apgcv1:policy:{_POLICY_SHA256}"
        or not same_typed_json_v1(
            LOWER_QUARTILE_MARGINAL_ENVELOPE_V1,
            _EXPECTED_POLICY_V1,
        )
    ):
        raise _error("frozen exploratory candidate policy metadata drifted in process")
    if canonical_json_sha256_v1(
        ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1
    ) != _SAFETY_PAYLOAD_SHA256 or not same_typed_json_v1(
        ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_SAFETY_V1,
        _EXPECTED_SAFETY_V1,
    ):
        raise _error("frozen exploratory candidate safety metadata drifted in process")


def _degree_class(degree: int) -> str:
    _require(
        type(degree) is int and degree >= 0,
        "candidate degree must be a nonnegative integer",
    )
    if degree == 0:
        return "ZERO"
    if degree == 1:
        return "ONE"
    return "MULTIPLE"


def _mask(checks: Mapping[str, bool], order: Sequence[str]) -> list[bool]:
    values = [checks[field] for field in order]
    _require(all(type(value) is bool for value in values), "envelope mask must contain booleans")
    return values


def _axis_checks(distance: Mapping[str, Any]) -> dict[str, bool]:
    values = {
        "x0_within_cap": distance["x0_median_absolute_distance_ppm"] <= _AXIS_X0_CAP,
        "x2_within_cap": distance["x2_median_absolute_distance_ppm"] <= _AXIS_X2_CAP,
        "doubled_center2_within_cap": (
            distance["center2_median_absolute_distance_ppm"] <= _AXIS_CENTER2_CAP
        ),
    }
    _require(
        all(
            type(distance[field]) is int
            for field in (
                "x0_median_absolute_distance_ppm",
                "x2_median_absolute_distance_ppm",
                "center2_median_absolute_distance_ppm",
            )
        ),
        "axis envelope requires exact upstream integer PPM distances",
    )
    return values


def _axis_distance_dispositions(
    relation: Mapping[str, Any],
) -> list[dict[str, Any]]:
    distances = relation["axis_cartesian_distances"]
    _require(type(distances) is list, "upstream axis distances must be an ordered list")
    distance_ids = [distance["axis_distance_id"] for distance in distances]
    _require(len(distance_ids) == len(set(distance_ids)), "upstream axis distance IDs repeat")

    checks_by_id = {distance["axis_distance_id"]: _axis_checks(distance) for distance in distances}
    passing = [
        distance
        for distance in distances
        if all(checks_by_id[distance["axis_distance_id"]].values())
    ]
    previous_degrees = Counter(distance["previous_axis_geometry_id"] for distance in passing)
    following_degrees = Counter(distance["following_axis_geometry_id"] for distance in passing)

    output = []
    for distance in distances:
        distance_id = distance["axis_distance_id"]
        checks = checks_by_id[distance_id]
        mask = _mask(checks, _AXIS_CHECK_FIELDS)
        within = all(mask)
        previous_degree = previous_degrees[distance["previous_axis_geometry_id"]]
        following_degree = following_degrees[distance["following_axis_geometry_id"]]
        singleton = within and previous_degree == 1 and following_degree == 1
        if not within:
            primary = _DISTANCE_OUTSIDE
        elif singleton:
            primary = _DISTANCE_SINGLETON
        else:
            primary = _DISTANCE_AMBIGUOUS
        payload: dict[str, Any] = {
            "page_pair_id": distance["page_pair_id"],
            "relation_id": relation["relation_id"],
            "axis_distance_id": distance_id,
            "relation_axis_distance_ordinal": distance["ordinal"],
            "previous_fragment_id": distance["previous_fragment_id"],
            "following_fragment_id": distance["following_fragment_id"],
            "previous_axis_geometry_id": distance["previous_axis_geometry_id"],
            "following_axis_geometry_id": distance["following_axis_geometry_id"],
            "axis_envelope_checks": checks,
            "axis_envelope_mask": mask,
            "axis_envelope_joint_pass": within,
            "failed_axis_envelope_components": [
                field for field in _AXIS_CHECK_FIELDS if not checks[field]
            ],
            "previous_axis_within_envelope_degree_in_relation": previous_degree,
            "following_axis_within_envelope_degree_in_relation": following_degree,
            "bidirectionally_singleton_axis_seed_link": singleton,
            "primary_disposition": primary,
            "outside_envelope_is_negative_claim": False,
        }
        payload["axis_distance_disposition_id"] = _content_id("axis_distance_disposition", payload)
        output.append(payload)
    return output


def _relation_disposition(
    relation: Mapping[str, Any],
    axis_dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    evidence = relation["table_distance_evidence"]
    integer_fields = (
        "normalized_left_edge_absolute_distance_ppm",
        "normalized_right_edge_absolute_distance_ppm",
        "normalized_width_absolute_distance_ppm",
        "previous_distance_to_page_bottom_ppm",
        "following_distance_from_page_top_ppm",
    )
    _require(
        all(type(evidence[field]) is int for field in integer_fields),
        "table and page envelopes require exact upstream integer PPM distances",
    )
    table_checks = {
        "left_edge_within_cap": (
            evidence["normalized_left_edge_absolute_distance_ppm"] <= _TABLE_LEFT_CAP
        ),
        "right_edge_within_cap": (
            evidence["normalized_right_edge_absolute_distance_ppm"] <= _TABLE_RIGHT_CAP
        ),
        "width_within_cap": (
            evidence["normalized_width_absolute_distance_ppm"] <= _TABLE_WIDTH_CAP
        ),
    }
    boundary_checks = {
        "previous_bottom_within_cap": (
            evidence["previous_distance_to_page_bottom_ppm"] <= _PREVIOUS_BOTTOM_CAP
        ),
        "following_top_within_cap": (
            evidence["following_distance_from_page_top_ppm"] <= _FOLLOWING_TOP_CAP
        ),
    }
    table_mask = _mask(table_checks, _TABLE_CHECK_FIELDS)
    boundary_mask = _mask(boundary_checks, _BOUNDARY_CHECK_FIELDS)
    joint_mask = [*table_mask, *boundary_mask]
    singleton_ids = [
        disposition["axis_distance_id"]
        for disposition in axis_dispositions
        if disposition["bidirectionally_singleton_axis_seed_link"]
    ]
    within_ids = [
        disposition["axis_distance_id"]
        for disposition in axis_dispositions
        if disposition["axis_envelope_joint_pass"]
    ]
    ambiguous_ids = [
        disposition["axis_distance_id"]
        for disposition in axis_dispositions
        if disposition["primary_disposition"] == _DISTANCE_AMBIGUOUS
    ]
    failure_mask = {
        "table_left_edge_outside_envelope": not table_checks["left_edge_within_cap"],
        "table_right_edge_outside_envelope": not table_checks["right_edge_within_cap"],
        "table_width_outside_envelope": not table_checks["width_within_cap"],
        "previous_bottom_outside_envelope": not boundary_checks["previous_bottom_within_cap"],
        "following_top_outside_envelope": not boundary_checks["following_top_within_cap"],
        "fewer_than_two_bidirectionally_singleton_axis_links": (
            len(singleton_ids) < _MINIMUM_SINGLETON_LINKS
        ),
    }
    table_and_boundary_pass = all(joint_mask)
    supported = table_and_boundary_pass and len(singleton_ids) >= _MINIMUM_SINGLETON_LINKS
    if not table_and_boundary_pass:
        primary = _RELATION_OUTSIDE
        primary_reason = "ONE_OR_MORE_TABLE_OR_PAGE_ENVELOPE_COMPONENTS_FAILED"
    elif not supported:
        primary = _RELATION_AXIS_INSUFFICIENT
        primary_reason = "UNCALIBRATED_MINIMUM_SINGLETON_AXIS_SUPPORT_NOT_MET"
    else:
        primary = _RELATION_SEED
        primary_reason = "ALL_ENVELOPES_AND_CONSERVATIVE_SEED_SUPPORT_RULE_MET"
    payload: dict[str, Any] = {
        "page_pair_id": relation["page_pair_id"],
        "relation_id": relation["relation_id"],
        "relation_ordinal": relation["ordinal"],
        "previous_fragment_id": relation["previous_fragment_id"],
        "following_fragment_id": relation["following_fragment_id"],
        "table_shape_envelope_checks": table_checks,
        "table_shape_envelope_mask": table_mask,
        "table_shape_envelope_joint_pass": all(table_mask),
        "page_boundary_envelope_checks": boundary_checks,
        "page_boundary_envelope_mask": boundary_mask,
        "page_boundary_envelope_joint_pass": all(boundary_mask),
        "table_page_joint_envelope_mask": joint_mask,
        "table_page_joint_envelope_pass": table_and_boundary_pass,
        "axis_distance_ids": [disposition["axis_distance_id"] for disposition in axis_dispositions],
        "within_axis_envelope_distance_ids": within_ids,
        "ambiguous_axis_envelope_distance_ids": ambiguous_ids,
        "bidirectionally_singleton_axis_seed_link_ids": singleton_ids,
        "bidirectionally_singleton_axis_seed_link_count": len(singleton_ids),
        "minimum_bidirectionally_singleton_axis_seed_links_required": (_MINIMUM_SINGLETON_LINKS),
        "relation_failure_mask": failure_mask,
        "relation_failure_reason_codes": [
            _RELATION_FAILURE_CODES[field]
            for field in _RELATION_FAILURE_FIELDS
            if failure_mask[field]
        ],
        "primary_disposition": primary,
        "primary_reason_code": primary_reason,
        "geometry_supported_exploratory_seed_candidate": supported,
        "outside_or_insufficient_is_negative_claim": False,
    }
    payload["relation_disposition_id"] = _content_id("relation_disposition", payload)
    return payload


def _relation_and_distance_dispositions(
    relations: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    relation_ids = [relation["relation_id"] for relation in relations]
    _require(len(relation_ids) == len(set(relation_ids)), "upstream relation IDs repeat")
    relation_output = []
    distance_output = []
    seen_distance_ids: set[str] = set()
    for relation in relations:
        local_distances = _axis_distance_dispositions(relation)
        local_ids = [item["axis_distance_id"] for item in local_distances]
        _require(
            not seen_distance_ids.intersection(local_ids),
            "an upstream axis distance occurs in more than one relation",
        )
        seen_distance_ids.update(local_ids)
        relation_output.append(_relation_disposition(relation, local_distances))
        for item in local_distances:
            item["ordinal"] = len(distance_output) + 1
            item["axis_distance_disposition_id"] = _content_id(
                "axis_distance_disposition",
                {
                    key: value
                    for key, value in item.items()
                    if key != "axis_distance_disposition_id"
                },
            )
            distance_output.append(item)
    return relation_output, distance_output


def _annotate_fragment_relation_degrees(
    relation_dispositions: Sequence[dict[str, Any]],
) -> None:
    supported = [
        item
        for item in relation_dispositions
        if item["geometry_supported_exploratory_seed_candidate"]
    ]
    previous_degrees = Counter(item["previous_fragment_id"] for item in supported)
    following_degrees = Counter(item["following_fragment_id"] for item in supported)
    for item in relation_dispositions:
        previous_degree = previous_degrees[item["previous_fragment_id"]]
        following_degree = following_degrees[item["following_fragment_id"]]
        reciprocal = (
            item["geometry_supported_exploratory_seed_candidate"]
            and previous_degree == 1
            and following_degree == 1
        )
        item["previous_fragment_geometry_supported_relation_degree"] = previous_degree
        item["previous_fragment_geometry_supported_relation_degree_class"] = _degree_class(
            previous_degree
        )
        item["following_fragment_geometry_supported_relation_degree"] = following_degree
        item["following_fragment_geometry_supported_relation_degree_class"] = _degree_class(
            following_degree
        )
        item["reciprocal_singleton_fragment_seed_candidate"] = reciprocal
        item["relation_disposition_id"] = _content_id(
            "relation_disposition",
            {key: value for key, value in item.items() if key != "relation_disposition_id"},
        )


def _fragment_dispositions(
    upstream: Mapping[str, Any],
    relation_dispositions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    fragments = upstream["table_fragments"]
    upstream_dispositions = upstream["fragment_dispositions"]
    fragment_ids = [fragment["fragment_id"] for fragment in fragments]
    _require(len(fragment_ids) == len(set(fragment_ids)), "upstream fragment IDs repeat in pair")
    by_fragment = {item["fragment_id"]: item for item in upstream_dispositions}
    _require(set(fragment_ids) == set(by_fragment), "upstream fragment dispositions are not closed")

    supported_relations = [
        item
        for item in relation_dispositions
        if item["geometry_supported_exploratory_seed_candidate"]
    ]
    supported_by_fragment: dict[str, list[Mapping[str, Any]]] = {}
    all_by_fragment: dict[str, list[Mapping[str, Any]]] = {}
    for item in relation_dispositions:
        for field in ("previous_fragment_id", "following_fragment_id"):
            all_by_fragment.setdefault(item[field], []).append(item)
    for item in supported_relations:
        for field in ("previous_fragment_id", "following_fragment_id"):
            supported_by_fragment.setdefault(item[field], []).append(item)
    degrees = {
        fragment_id: len(supported_by_fragment.get(fragment_id, [])) for fragment_id in fragment_ids
    }

    output = []
    for fragment in fragments:
        fragment_id = fragment["fragment_id"]
        source = by_fragment[fragment_id]
        incident = all_by_fragment.get(fragment_id, [])
        supported = supported_by_fragment.get(fragment_id, [])
        _require(
            source["relation_ids"] == [item["relation_id"] for item in incident],
            "upstream fragment relation incidence drifted",
        )
        degree = degrees[fragment_id]
        reciprocal_ids = []
        if degree == 1:
            relation = supported[0]
            counterpart = (
                relation["following_fragment_id"]
                if relation["previous_fragment_id"] == fragment_id
                else relation["previous_fragment_id"]
            )
            if degrees[counterpart] == 1:
                reciprocal_ids.append(relation["relation_id"])
        if source["primary_disposition"] != _UPSTREAM_MEASURED_FRAGMENT:
            _require(degree == 0 and not incident, "retained upstream fragment entered eligibility")
            primary = _FRAGMENT_UPSTREAM_RETAINED
        elif degree == 0:
            primary = _FRAGMENT_ZERO
        elif degree == 1 and reciprocal_ids:
            primary = _FRAGMENT_RECIPROCAL
        elif degree == 1:
            primary = _FRAGMENT_ONE_SIDED
        else:
            primary = _FRAGMENT_MULTIPLE
        payload: dict[str, Any] = {
            "ordinal": len(output) + 1,
            "page_pair_id": source["page_pair_id"],
            "fragment_id": fragment_id,
            "side": source["side"],
            "table_node_id": source["table_node_id"],
            "upstream_fragment_disposition_id": source["fragment_disposition_id"],
            "upstream_primary_disposition": source["primary_disposition"],
            "upstream_reason_code": source["reason_code"],
            "upstream_incident_relation_ids": list(source["relation_ids"]),
            "geometry_supported_relation_ids": [item["relation_id"] for item in supported],
            "reciprocal_singleton_fragment_relation_ids": reciprocal_ids,
            "geometry_supported_relation_degree": degree,
            "geometry_supported_relation_degree_class": _degree_class(degree),
            "primary_disposition": primary,
            "unmatched_or_ambiguous_is_negative_claim": False,
        }
        payload["fragment_disposition_id"] = _content_id("fragment_disposition", payload)
        output.append(payload)
    return output


def _physical_axis_dispositions(
    upstream: Mapping[str, Any],
    distance_dispositions: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    by_distance = {item["axis_distance_id"]: item for item in distance_dispositions}
    _require(
        len(by_distance) == len(distance_dispositions),
        "gate axis-distance dispositions repeat an upstream distance",
    )
    output = []
    for source in upstream["axis_dispositions"]:
        incident_ids = source["axis_distance_ids"]
        _require(
            all(distance_id in by_distance for distance_id in incident_ids),
            "upstream physical axis cites a foreign axis distance",
        )
        incident = [by_distance[distance_id] for distance_id in incident_ids]
        within_ids = [
            item["axis_distance_id"] for item in incident if item["axis_envelope_joint_pass"]
        ]
        singleton_ids = [
            item["axis_distance_id"]
            for item in incident
            if item["bidirectionally_singleton_axis_seed_link"]
        ]
        ambiguous_ids = [
            item["axis_distance_id"]
            for item in incident
            if item["primary_disposition"] == _DISTANCE_AMBIGUOUS
        ]
        outside_ids = [
            item["axis_distance_id"]
            for item in incident
            if item["primary_disposition"] == _DISTANCE_OUTSIDE
        ]
        if source["primary_disposition"] != _UPSTREAM_MEASURED_AXIS:
            _require(not incident_ids, "retained upstream axis entered eligibility")
            primary = _AXIS_UPSTREAM_RETAINED
        elif not within_ids:
            primary = _AXIS_ZERO
        elif not singleton_ids:
            primary = _AXIS_AMBIGUOUS_ONLY
        elif len(singleton_ids) == 1 and len(within_ids) == 1:
            primary = _AXIS_ONE_SINGLETON
        else:
            primary = _AXIS_MIXED
        payload: dict[str, Any] = {
            "ordinal": len(output) + 1,
            "page_pair_id": source["page_pair_id"],
            "fragment_id": source["fragment_id"],
            "side": source["side"],
            "axis_geometry_id": source["axis_geometry_id"],
            "axis_node_id": source["axis_node_id"],
            "upstream_axis_disposition_id": source["axis_disposition_id"],
            "upstream_primary_disposition": source["primary_disposition"],
            "upstream_reason_code": source["reason_code"],
            "upstream_incident_axis_distance_ids": list(incident_ids),
            "within_axis_envelope_distance_ids": within_ids,
            "bidirectionally_singleton_axis_seed_link_ids": singleton_ids,
            "ambiguous_axis_envelope_distance_ids": ambiguous_ids,
            "outside_axis_envelope_distance_ids": outside_ids,
            "within_axis_envelope_degree": len(within_ids),
            "within_axis_envelope_degree_class": _degree_class(len(within_ids)),
            "bidirectionally_singleton_axis_seed_link_degree": len(singleton_ids),
            "bidirectionally_singleton_axis_seed_link_degree_class": _degree_class(
                len(singleton_ids)
            ),
            "within_axis_envelope_distance_count": len(within_ids),
            "bidirectionally_singleton_axis_seed_link_count": len(singleton_ids),
            "ambiguous_axis_envelope_distance_count": len(ambiguous_ids),
            "outside_axis_envelope_distance_count": len(outside_ids),
            "primary_disposition": primary,
            "unmatched_or_ambiguous_is_negative_claim": False,
        }
        payload["axis_disposition_id"] = _content_id("axis_disposition", payload)
        output.append(payload)
    return output


def _page_pair_disposition(
    upstream: Mapping[str, Any],
    relation_dispositions: Sequence[Mapping[str, Any]],
    fragment_dispositions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    source = upstream["page_pair_disposition"]
    supported_ids = [
        item["relation_id"]
        for item in relation_dispositions
        if item["geometry_supported_exploratory_seed_candidate"]
    ]
    reciprocal_ids = sorted(
        {
            relation_id
            for item in fragment_dispositions
            for relation_id in item["reciprocal_singleton_fragment_relation_ids"]
        },
        key=supported_ids.index,
    )
    ambiguous_ids = [
        relation_id for relation_id in supported_ids if relation_id not in reciprocal_ids
    ]
    if source["primary_disposition"] != _UPSTREAM_MEASURED_PAIR:
        _require(
            not relation_dispositions and not supported_ids, "nonmeasured pair entered eligibility"
        )
        primary = _PAIR_UPSTREAM_RETAINED
    elif not supported_ids:
        primary = _PAIR_NO_SEED
    elif ambiguous_ids:
        primary = _PAIR_AMBIGUOUS
    else:
        primary = _PAIR_RECIPROCAL
    payload: dict[str, Any] = {
        "page_pair_id": source["page_pair_id"],
        "upstream_page_pair_disposition_id": source["page_pair_disposition_id"],
        "upstream_primary_disposition": source["primary_disposition"],
        "upstream_reason_code": source["reason_code"],
        "upstream_relation_count": source["emitted_cartesian_relation_count"],
        "relation_ids": [item["relation_id"] for item in relation_dispositions],
        "geometry_supported_relation_ids": supported_ids,
        "reciprocal_singleton_fragment_relation_ids": reciprocal_ids,
        "fragment_ambiguous_geometry_supported_relation_ids": ambiguous_ids,
        "primary_disposition": primary,
        "zero_or_ambiguous_is_negative_claim": False,
        "source_table_absence_claimed": False,
    }
    payload["page_pair_disposition_id"] = _content_id("page_pair_disposition", payload)
    return payload


def _fixed_counts(values: Sequence[Mapping[str, Any]], choices: Sequence[str]) -> dict[str, int]:
    counts = Counter(item["primary_disposition"] for item in values)
    _require(set(counts).issubset(choices), "a disposition escaped its closed partition")
    return {choice: counts[choice] for choice in choices}


def _metrics(
    upstream: Mapping[str, Any],
    relation_dispositions: Sequence[Mapping[str, Any]],
    distance_dispositions: Sequence[Mapping[str, Any]],
    fragment_dispositions: Sequence[Mapping[str, Any]],
    axis_dispositions: Sequence[Mapping[str, Any]],
    page_pair_disposition: Mapping[str, Any],
) -> dict[str, Any]:
    relations = upstream["fragment_pair_relations"]
    fragments = upstream["table_fragments"]
    physical_axes = upstream["axis_dispositions"]
    upstream_distance_count = sum(
        len(relation["axis_cartesian_distances"]) for relation in relations
    )
    relation_degrees = Counter(
        item["geometry_supported_relation_degree_class"] for item in fragment_dispositions
    )
    axis_degrees = Counter(item["within_axis_envelope_degree_class"] for item in axis_dispositions)
    relation_counts = _fixed_counts(relation_dispositions, _RELATION_DISPOSITIONS)
    distance_counts = _fixed_counts(distance_dispositions, _DISTANCE_DISPOSITIONS)
    fragment_counts = _fixed_counts(fragment_dispositions, _FRAGMENT_DISPOSITIONS)
    axis_counts = _fixed_counts(axis_dispositions, _AXIS_DISPOSITIONS)
    pair_counts = Counter({page_pair_disposition["primary_disposition"]: 1})
    upstream_pair_counts = Counter({upstream["page_pair_disposition"]["primary_disposition"]: 1})
    return {
        "page_pair_count": 1,
        "input_relation_count": len(relations),
        "relation_disposition_count": len(relation_dispositions),
        "input_axis_distance_count": upstream_distance_count,
        "axis_distance_disposition_count": len(distance_dispositions),
        "input_fragment_count": len(fragments),
        "fragment_disposition_count": len(fragment_dispositions),
        "input_physical_axis_count": len(physical_axes),
        "physical_axis_disposition_count": len(axis_dispositions),
        "relation_no_drop": len(relations) == len(relation_dispositions),
        "axis_distance_no_drop": upstream_distance_count == len(distance_dispositions),
        "fragment_no_drop": len(fragments) == len(fragment_dispositions),
        "physical_axis_no_drop": len(physical_axes) == len(axis_dispositions),
        "relation_disposition_counts": relation_counts,
        "axis_distance_disposition_counts": distance_counts,
        "fragment_disposition_counts": fragment_counts,
        "physical_axis_disposition_counts": axis_counts,
        "fragment_geometry_supported_degree_counts": {
            degree: relation_degrees[degree] for degree in ("ZERO", "ONE", "MULTIPLE")
        },
        "physical_axis_within_envelope_degree_counts": {
            degree: axis_degrees[degree] for degree in ("ZERO", "ONE", "MULTIPLE")
        },
        "table_shape_component_pass_counts": {
            field: sum(item["table_shape_envelope_checks"][field] for item in relation_dispositions)
            for field in _TABLE_CHECK_FIELDS
        },
        "page_boundary_component_pass_counts": {
            field: sum(
                item["page_boundary_envelope_checks"][field] for item in relation_dispositions
            )
            for field in _BOUNDARY_CHECK_FIELDS
        },
        "axis_component_pass_counts": {
            field: sum(item["axis_envelope_checks"][field] for item in distance_dispositions)
            for field in _AXIS_CHECK_FIELDS
        },
        "table_shape_joint_pass_count": sum(
            item["table_shape_envelope_joint_pass"] for item in relation_dispositions
        ),
        "page_boundary_joint_pass_count": sum(
            item["page_boundary_envelope_joint_pass"] for item in relation_dispositions
        ),
        "table_page_joint_pass_count": sum(
            item["table_page_joint_envelope_pass"] for item in relation_dispositions
        ),
        "axis_joint_pass_count": sum(
            item["axis_envelope_joint_pass"] for item in distance_dispositions
        ),
        "upstream_retained_fragment_count": sum(
            item["upstream_primary_disposition"] != _UPSTREAM_MEASURED_FRAGMENT
            for item in fragment_dispositions
        ),
        "upstream_retained_physical_axis_count": sum(
            item["upstream_primary_disposition"] != _UPSTREAM_MEASURED_AXIS
            for item in axis_dispositions
        ),
        "upstream_page_pair_disposition_counts": {
            choice: upstream_pair_counts[choice] for choice in _UPSTREAM_PAIR_DISPOSITIONS
        },
        "page_pair_disposition_counts": {
            choice: pair_counts[choice] for choice in _PAIR_DISPOSITIONS
        },
    }


def _upstream_binding(upstream: Mapping[str, Any]) -> dict[str, Any]:
    relations = upstream["fragment_pair_relations"]
    distance_ids = [
        distance["axis_distance_id"]
        for relation in relations
        for distance in relation["axis_cartesian_distances"]
    ]
    return {
        "upstream_artifact_identity": upstream["artifact_identity"],
        "upstream_artifact_sha256": canonical_json_sha256_v1(upstream),
        "upstream_format_version": upstream["format_version"],
        "upstream_claim_boundary": upstream["claim_boundary"],
        "upstream_status": upstream["status"],
        "page_pair_id": upstream["ordered_page_pair"]["page_pair_id"],
        "upstream_page_pair_disposition_id": upstream["page_pair_disposition"][
            "page_pair_disposition_id"
        ],
        "upstream_page_pair_primary_disposition": upstream["page_pair_disposition"][
            "primary_disposition"
        ],
        "fragment_ids": [item["fragment_id"] for item in upstream["table_fragments"]],
        "relation_ids": [item["relation_id"] for item in relations],
        "axis_distance_ids": distance_ids,
        "upstream_fragment_disposition_ids": [
            item["fragment_disposition_id"] for item in upstream["fragment_dispositions"]
        ],
        "axis_geometry_ids": [item["axis_geometry_id"] for item in upstream["axis_dispositions"]],
        "upstream_axis_disposition_ids": [
            item["axis_disposition_id"] for item in upstream["axis_dispositions"]
        ],
    }


def _derive_from_validated_relation(upstream: Mapping[str, Any]) -> dict[str, Any]:
    """Pure composition boundary for an already public-built exact relation set."""

    _validate_static_contract_integrity()
    relations = upstream["fragment_pair_relations"]
    relation_dispositions, distance_dispositions = _relation_and_distance_dispositions(relations)
    _annotate_fragment_relation_degrees(relation_dispositions)
    fragment_dispositions = _fragment_dispositions(upstream, relation_dispositions)
    axis_dispositions = _physical_axis_dispositions(upstream, distance_dispositions)
    pair_disposition = _page_pair_disposition(
        upstream,
        relation_dispositions,
        fragment_dispositions,
    )
    artifact: dict[str, Any] = {
        "format_version": ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_FORMAT_VERSION_V1,
        "claim_boundary": ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_CLAIM_BOUNDARY_V1,
        "status": ADJACENT_PAGE_TABLE_GEOMETRY_CANDIDATE_GATE_STATUS_V1,
        "policy": canonical_clone_v1(_EXPECTED_POLICY_V1),
        "policy_identity": _EXPECTED_POLICY_V1["policy_identity"],
        "safety_payload_sha256": _SAFETY_PAYLOAD_SHA256,
        "upstream_binding": _upstream_binding(upstream),
        "relation_dispositions": relation_dispositions,
        "axis_distance_dispositions": distance_dispositions,
        "fragment_dispositions": fragment_dispositions,
        "axis_dispositions": axis_dispositions,
        "page_pair_disposition": pair_disposition,
        "metrics": _metrics(
            upstream,
            relation_dispositions,
            distance_dispositions,
            fragment_dispositions,
            axis_dispositions,
            pair_disposition,
        ),
        "safety": canonical_clone_v1(_EXPECTED_SAFETY_V1),
    }
    artifact["artifact_identity"] = _content_id("artifact", artifact)
    return canonical_clone_v1(artifact)


def build_adjacent_page_table_geometry_candidate_gate_v1(
    previous_projection: Mapping[str, Any],
    previous_proposal_projection: Mapping[str, Any],
    previous_graph: Mapping[str, Any],
    following_projection: Mapping[str, Any],
    following_proposal_projection: Mapping[str, Any],
    following_graph: Mapping[str, Any],
) -> dict[str, Any]:
    """Build the upstream relation once, then account every exploratory seed."""

    try:
        upstream = build_adjacent_page_table_geometry_relations_v1(
            previous_projection,
            previous_proposal_projection,
            previous_graph,
            following_projection,
            following_proposal_projection,
            following_graph,
        )
        return _derive_from_validated_relation(upstream)
    except ValueError as exc:
        if isinstance(exc, AdjacentPageTableGeometryCandidateGateError):
            raise
        raise _error(
            "candidate gate input failed exact adjacent-page relation construction"
        ) from exc


def validate_adjacent_page_table_geometry_candidate_gate_v1(
    value: Any,
    *,
    previous_projection: Mapping[str, Any],
    previous_proposal_projection: Mapping[str, Any],
    previous_graph: Mapping[str, Any],
    following_projection: Mapping[str, Any],
    following_proposal_projection: Mapping[str, Any],
    following_graph: Mapping[str, Any],
) -> dict[str, Any]:
    """Typed-replay the fused gate from all six authenticated page inputs."""

    if type(value) is not dict:
        raise _error("adjacent-page geometry candidate gate must be a plain object")
    expected = build_adjacent_page_table_geometry_candidate_gate_v1(
        previous_projection,
        previous_proposal_projection,
        previous_graph,
        following_projection,
        following_proposal_projection,
        following_graph,
    )
    if not same_typed_json_v1(value, expected):
        raise _error("adjacent-page geometry candidate gate drifted from exact fused replay")
    return canonical_clone_v1(expected)
