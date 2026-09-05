from __future__ import annotations

import copy

import pytest

from bctc_ai.evaluation.source_reference_identity_v1 import (
    SourceReferenceIdentityV1Error,
    stable_unique_source_refs_v1,
)


def test_stable_unique_uses_exact_canonical_bytes_and_preserves_first_order() -> None:
    first = {
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "table_id": "t1",
        },
        "row_id": "r1",
    }
    same_row_other_locator = {
        "locator": {
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
            "table_id": "t2",
        },
        "row_id": "r1",
    }
    near_duplicate = {
        **copy.deepcopy(first),
        "row_kind": "ITEM",
    }
    reordered_exact_duplicate = {
        "row_id": "r1",
        "locator": {
            "table_id": "t1",
            "page_json_version_id": "gfpstorev1:json:" + "1" * 64,
        },
    }
    source_refs = [
        first,
        same_row_other_locator,
        reordered_exact_duplicate,
        near_duplicate,
        copy.deepcopy(first),
    ]
    before = copy.deepcopy(source_refs)

    result = stable_unique_source_refs_v1(source_refs)

    assert result == [first, same_row_other_locator, near_duplicate]
    assert source_refs == before
    assert all(
        actual is not original
        for actual, original in zip(
            result, [first, same_row_other_locator, near_duplicate], strict=True
        )
    )


def test_stable_unique_preserves_exact_json_type_distinctions() -> None:
    assert stable_unique_source_refs_v1(
        [{"row_id": "r1", "ordinal": 1}, {"row_id": "r1", "ordinal": 1.0}]
    ) == [{"ordinal": 1, "row_id": "r1"}, {"ordinal": 1.0, "row_id": "r1"}]


def test_stable_unique_accepts_empty_source_ref_axis() -> None:
    assert stable_unique_source_refs_v1([]) == []


@pytest.mark.parametrize("source_refs", [None, "r1", [None], [{1: "r1"}]])
def test_stable_unique_rejects_malformed_source_ref_axes(source_refs: object) -> None:
    with pytest.raises(SourceReferenceIdentityV1Error):
        stable_unique_source_refs_v1(source_refs)  # type: ignore[arg-type]
