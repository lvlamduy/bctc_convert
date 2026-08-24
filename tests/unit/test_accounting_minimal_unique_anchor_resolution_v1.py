from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.accounting_minimal_unique_anchor_resolution_v1 import (
    AccountingMinimalUniqueAnchorResolutionV1Error,
    build_accounting_minimal_unique_anchor_resolution_v1,
    validate_accounting_minimal_unique_anchor_resolution_replay_v1,
)


def _candidate(
    candidate_id: str,
    *,
    children: list[str],
    disposition: str = "COMPLETE",
    parent: str | None = "PARENT_FAMILY",
) -> dict:
    return {
        "candidate_id": candidate_id,
        "child_anchor_ids": children,
        "disposition": disposition,
        "parent_anchor_id": parent,
    }


def _resolution(result: dict, candidate_id: str) -> dict:
    return next(
        item["resolution"] for item in result["candidates"] if item["candidate_id"] == candidate_id
    )


def test_parent_child_pair_is_preferred_and_near_candidates_control_uniqueness() -> None:
    candidates = [
        _candidate("complete-a", children=["CHILD_A", "CHILD_B"]),
        _candidate("near-a", children=["CHILD_A"], disposition="NEAR"),
    ]

    result = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-1"
    )

    resolution = _resolution(result, "complete-a")
    assert resolution["selected_anchor_ids"] == ["PARENT_FAMILY", "CHILD_B"]
    assert resolution["selected_size"] == 2
    assert resolution["matching_candidate_ids"] == ["complete-a"]
    assert resolution["matching_count"] == 1
    assert resolution["searched_triple_count"] == 0
    assert result["candidate_ids"] == ["complete-a", "near-a"]
    assert result["safety"]["complete_and_near_candidates_share_comparison_scope"] is True


def test_child_child_pair_is_selected_only_after_every_parent_child_pair_collides() -> None:
    candidates = [
        _candidate("complete-ab", children=["CHILD_A", "CHILD_B"]),
        _candidate("near-a", children=["CHILD_A"], disposition="NEAR"),
        _candidate("near-b", children=["CHILD_B"], disposition="NEAR"),
    ]

    result = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-child-pair"
    )

    resolution = _resolution(result, "complete-ab")
    assert resolution["selected_anchor_ids"] == ["CHILD_A", "CHILD_B"]
    assert resolution["selected_size"] == 2
    assert resolution["searched_pair_count"] == 3
    assert resolution["parent_child_pairs_precede_child_child_pairs"] is True


def test_two_complete_regions_need_triples_only_with_additional_near_pair_controls() -> None:
    # With exactly two set-based candidates, triple-only uniqueness is impossible:
    # a second set containing every pair of three anchors also contains the triple.
    # Near controls make every pair collide while allowing a triple to distinguish
    # each of the two complete candidates across the full candidate ledger.
    candidates = [
        _candidate("complete-abc", children=["A", "B", "C"]),
        _candidate("complete-abd", children=["A", "B", "D"]),
        _candidate("near-pc", children=["C"], disposition="NEAR"),
        _candidate("near-ac", children=["A", "C"], disposition="NEAR", parent=None),
        _candidate("near-bc", children=["B", "C"], disposition="NEAR", parent=None),
        _candidate("near-pd", children=["D"], disposition="NEAR"),
        _candidate("near-ad", children=["A", "D"], disposition="NEAR", parent=None),
        _candidate("near-bd", children=["B", "D"], disposition="NEAR", parent=None),
    ]

    result = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-triples"
    )

    abc = _resolution(result, "complete-abc")
    abd = _resolution(result, "complete-abd")
    assert abc["selected_anchor_ids"] == ["PARENT_FAMILY", "A", "C"]
    assert abd["selected_anchor_ids"] == ["PARENT_FAMILY", "A", "D"]
    assert abc["selected_size"] == abd["selected_size"] == 3
    assert abc["searched_pair_count"] == abd["searched_pair_count"] == 6
    assert abc["pair_combinations_exhausted_before_triples"] is True


def test_all_pair_and_triple_collisions_remain_unresolved() -> None:
    candidates = [
        _candidate("complete-a", children=["A", "B", "C"]),
        _candidate("near-copy", children=["A", "B", "C"], disposition="NEAR"),
    ]

    result = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-collision"
    )

    resolution = _resolution(result, "complete-a")
    assert resolution["status"] == "UNRESOLVED_NO_UNIQUE_PAIR_OR_TRIPLE_COMBINATION"
    assert resolution["selected_anchor_ids"] == []
    assert resolution["matching_candidate_ids"] == ["complete-a", "near-copy"]
    assert resolution["matching_count"] == 2
    assert resolution["searched_pair_count"] == 6
    assert resolution["searched_triple_count"] == 4


def test_provider_and_child_reordering_is_canonical() -> None:
    candidates = [
        _candidate("complete", children=["CHILD_B", "CHILD_A"]),
        _candidate("near", children=["CHILD_A"], disposition="NEAR"),
    ]
    expected = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-order"
    )
    reordered = copy.deepcopy(list(reversed(candidates)))
    for candidate in reordered:
        candidate["child_anchor_ids"].reverse()

    assert (
        build_accounting_minimal_unique_anchor_resolution_v1(
            reordered, document_scope_id="document-order"
        )
        == expected
    )


def test_missing_parent_or_child_cannot_invent_a_two_anchor_resolution() -> None:
    result = build_accounting_minimal_unique_anchor_resolution_v1(
        [
            _candidate("parent-only", children=[]),
            _candidate("child-only", children=["CHILD_A"], parent=None),
        ],
        document_scope_id="document-insufficient",
    )

    for candidate_id in ("parent-only", "child-only"):
        resolution = _resolution(result, candidate_id)
        assert resolution["status"] == "UNRESOLVED_INSUFFICIENT_TWO_ANCHOR_COMBINATION"
        assert resolution["selected_size"] is None


@pytest.mark.parametrize(
    "mutate",
    [
        lambda item: item.update(extra=True),
        lambda item: item.update(disposition="UNKNOWN"),
        lambda item: item.update(child_anchor_ids=["CHILD_A", "CHILD_A"]),
        lambda item: item.update(parent_anchor_id="CHILD_A"),
        lambda item: item.update(parent_anchor_id=None, child_anchor_ids=[]),
        lambda item: item.update(candidate_id="e\N{COMBINING ACUTE ACCENT}"),
    ],
)
def test_malformed_candidate_contract_fails_closed(mutate: object) -> None:
    candidate = _candidate("complete", children=["CHILD_A"])
    mutate(candidate)

    with pytest.raises(AccountingMinimalUniqueAnchorResolutionV1Error):
        build_accounting_minimal_unique_anchor_resolution_v1(
            [candidate], document_scope_id="document-malformed"
        )


def test_duplicate_candidate_id_fails_closed() -> None:
    candidate = _candidate("duplicate", children=["CHILD_A"])

    with pytest.raises(
        AccountingMinimalUniqueAnchorResolutionV1Error,
        match="candidate ID repeats",
    ):
        build_accounting_minimal_unique_anchor_resolution_v1(
            [candidate, copy.deepcopy(candidate)],
            document_scope_id="document-duplicate",
        )


def test_exact_replay_and_tamper_rejection() -> None:
    candidates = [_candidate("complete", children=["CHILD_A"])]
    result = build_accounting_minimal_unique_anchor_resolution_v1(
        candidates, document_scope_id="document-replay"
    )

    assert (
        validate_accounting_minimal_unique_anchor_resolution_replay_v1(
            result,
            candidates,
            document_scope_id="document-replay",
        )
        == result
    )
    tampered = copy.deepcopy(result)
    tampered["candidates"][0]["resolution"]["matching_count"] = 2
    with pytest.raises(
        AccountingMinimalUniqueAnchorResolutionV1Error,
        match="content identity drifted",
    ):
        validate_accounting_minimal_unique_anchor_resolution_replay_v1(
            tampered,
            candidates,
            document_scope_id="document-replay",
        )
