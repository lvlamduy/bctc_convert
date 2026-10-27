"""canonical_json_sha256_v1 and canonical_clone_v1 avoid rendering large trees but stay exactly equivalent."""

from __future__ import annotations

import json
import random
import tracemalloc
from enum import IntEnum
from hashlib import sha256

import pytest

from bctc_ai.source_structure import contracts_v1
from bctc_ai.source_structure.contracts_v1 import (
    SourceStructureContractError,
    canonical_clone_v1,
    canonical_json_bytes_v1,
    canonical_json_sha256_v1,
    decode_canonical_json_bytes_v1,
    same_typed_json_v1,
)

VECTORS = [
    None, True, False, 0, -1, 2**200, -(2**70), 0.0, -0.0, 0.1, 1e308, 5e-324, 1e16, 123456789.0, -2.5e-7,
    "", "a", 'quote " backslash \\ slash /', "\x00\x01\x1f\x7f", "  ", "Tiền gửi khách hàng",
    "é", "\U0001d518 non-BMP", "﻿BOM",
    [], {}, [[]], {"": {}}, [None, [True, [1.5, ["x"]]]],
    {"b": 1, "a": 2, "A": 3, "é": 4, "\U0001d518": 5, "10": 6, "9": 7},
    {"nested": {"z": [1, 2, {"y": None, "x": -0.0}], "a": "Triệu VND"}},
]

INVALID = [
    float("nan"), float("inf"), -float("inf"), "\ud800 lone", {"\udc00": 1}, (1, 2), {1, 2}, b"bytes",
    {1: "int key"}, {True: "bool key"}, {None: 1}, [object()], 1 + 2j, 10**5000, {"big": [-(10**4400)]},
]


class _Small(IntEnum):
    ONE = 1


@pytest.fixture(params=["one_shot", "streamed"])
def path(request, monkeypatch):
    if request.param == "streamed":
        monkeypatch.setattr(contracts_v1, "_STREAMED_HASH_MIN_NODES", 0)
        monkeypatch.setattr(contracts_v1, "_STREAMED_HASH_BATCH_CHARS", 7)
    return request.param


def _random_tree(rng: random.Random, depth: int) -> object:
    roll = rng.random()
    if depth <= 0 or roll < 0.35:
        return rng.choice([
            None, True, False, rng.randint(-(10**30), 10**30), rng.uniform(-1e6, 1e6), -0.0,
            "".join(rng.choice("aZ09 -_\"\\/éạ \U0001f600\x00\t") for _ in range(rng.randint(0, 12))),
        ])
    if roll < 0.7:
        return [_random_tree(rng, depth - 1) for _ in range(rng.randint(0, 5))]
    return {"".join(rng.choice("abcXYZé\U0001f600 ") for _ in range(rng.randint(0, 6))): _random_tree(rng, depth - 1)
            for _ in range(rng.randint(0, 5))}


@pytest.mark.parametrize("value", VECTORS, ids=range(len(VECTORS)))
def test_vectors_hash_exact_canonical_bytes(path, value):
    assert canonical_json_sha256_v1(value) == sha256(canonical_json_bytes_v1(value)).hexdigest()


def test_whole_vector_list_and_random_trees(path):
    assert canonical_json_sha256_v1(VECTORS) == sha256(canonical_json_bytes_v1(VECTORS)).hexdigest()
    rng = random.Random(20261028)
    for _ in range(300):
        tree = _random_tree(rng, 6)
        assert canonical_json_sha256_v1(tree) == sha256(canonical_json_bytes_v1(tree)).hexdigest()


@pytest.mark.parametrize("value", [*INVALID, _Small.ONE, [_Small.ONE]], ids=range(len(INVALID) + 2))
def test_invalid_values_raise_the_same_contract_error(path, value):
    with pytest.raises(SourceStructureContractError):
        canonical_json_bytes_v1(value)
    with pytest.raises(SourceStructureContractError):
        canonical_json_sha256_v1(value)


def test_default_threshold_selects_streaming_only_for_large_trees(monkeypatch):
    calls = []
    original = contracts_v1._canonical_json_bytes_validated
    monkeypatch.setattr(contracts_v1, "_canonical_json_bytes_validated", lambda value: calls.append(1) or original(value))
    small = {"rows": list(range(1000))}
    large = {"rows": list(range(contracts_v1._STREAMED_HASH_MIN_NODES))}
    assert canonical_json_sha256_v1(small) == sha256(original(small)).hexdigest()
    assert calls == [1]
    assert canonical_json_sha256_v1(large) == sha256(original(large)).hexdigest()
    assert calls == [1]  # the large tree was streamed; only the direct reference call rendered it


def _traced_peak(function, value):
    tracemalloc.start()
    try:
        result = function(value)
        return result, tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def test_streamed_hash_peak_is_flat_and_far_below_the_rendering():
    peaks = []
    for count in (30_000, 90_000):
        value = {"trials": [{"document": f"doc-{index:06d}", "values": [index, index * 1.5, "Triệu VND", None, True]}
                            for index in range(count)]}
        rendered, one_shot_peak = _traced_peak(canonical_json_bytes_v1, value)
        digest, streamed_peak = _traced_peak(canonical_json_sha256_v1, value)
        assert digest == sha256(rendered).hexdigest()
        assert streamed_peak * 10 < one_shot_peak
        peaks.append((len(rendered), streamed_peak))
    (small_size, small_peak), (large_size, large_peak) = peaks
    assert large_size > 2.5 * small_size
    assert large_peak < 1.25 * small_peak + 65_536  # independent of the rendered size


def _old_clone(value):
    return decode_canonical_json_bytes_v1(canonical_json_bytes_v1(value))


def _ordered(value):
    """Order-sensitive spelling: dict insertion order and float bits both matter."""
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


def _assert_same_clone(value):
    old = _old_clone(value)
    new = canonical_clone_v1(value)
    assert same_typed_json_v1(new, old)
    assert _ordered(new) == _ordered(old)
    assert canonical_json_bytes_v1(new) == canonical_json_bytes_v1(value)
    return new


@pytest.mark.parametrize("value", VECTORS, ids=range(len(VECTORS)))
def test_clone_vectors_equal_decoded_canonical_bytes(path, value):
    _assert_same_clone(value)


def test_clone_random_trees_and_independence(path):
    rng = random.Random(28102026)
    for _ in range(300):
        _assert_same_clone(_random_tree(rng, 6))
    shared = [1, {"z": 2, "a": [3]}]
    source = {"b": shared, "a": shared}
    clone = _assert_same_clone(source)
    assert list(clone) == ["a", "b"] and clone["a"] is not clone["b"]
    clone["a"][1]["a"].append(4)
    assert source == {"b": [1, {"z": 2, "a": [3]}], "a": [1, {"z": 2, "a": [3]}]}


@pytest.mark.parametrize("value", [*INVALID, _Small.ONE, [_Small.ONE]], ids=range(len(INVALID) + 2))
def test_clone_invalid_values_raise_the_same_contract_error(path, value):
    with pytest.raises(SourceStructureContractError):
        _old_clone(value)
    with pytest.raises(SourceStructureContractError):
        canonical_clone_v1(value)


def test_large_clone_does_not_render():
    peaks = []
    for count in (30_000, 90_000):
        value = {"trials": [{"document": f"doc-{index:06d}", "values": [index, index * 1.5, "Triệu VND", None, True]}
                            for index in range(count)]}
        old, old_peak = _traced_peak(_old_clone, value)
        new, new_peak = _traced_peak(canonical_clone_v1, value)
        assert _ordered(new) == _ordered(old)
        rendered = len(canonical_json_bytes_v1(value))
        assert new_peak < old_peak
        peaks.append((rendered, old_peak, new_peak))
    # The rebuilt containers are the result itself; the old path additionally holds three renderings.
    for rendered, old_peak, new_peak in peaks:
        assert old_peak - new_peak > 2 * rendered
