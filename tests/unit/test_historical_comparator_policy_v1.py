from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest

from bctc_ai.evaluation import historical_comparator_policy_v1 as policy_v1


def _sha(number: int) -> str:
    return f"{number:064x}"


def _page(number: int) -> str:
    return f"gfpstorev1:json:{number:064x}"


def _write_oracle(
    root: Path,
    *,
    name: str,
    format_version: str,
    source_sha256s: list[str],
) -> dict[str, object]:
    value = {
        "format_version": format_version,
        "trials": [
            {
                "source_pdf": {"sha256": source_sha256},
                "status": "READY" if index % 2 == 0 else "NOT_OBSERVED",
            }
            for index, source_sha256 in enumerate(source_sha256s)
        ],
    }
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    (root / name).write_bytes(payload)
    return {
        "expected_trial_count": len(source_sha256s),
        "format_version": format_version,
        "path": name,
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, object]:
    monkeypatch.setattr(policy_v1, "_PROJECT_ROOT", tmp_path)
    oracle_sources = [_sha(1), _sha(2)]
    oracle_ref = _write_oracle(
        tmp_path,
        name="oracle.json",
        format_version="TEST_ORACLE_V1",
        source_sha256s=oracle_sources,
    )
    current_sources = [*oracle_sources, _sha(3)]
    pages = [_page(1), _page(2), _page(3)]
    return {
        "policy": policy_v1.STRICT_RELEASE,
        "pinned_oracle_refs": [oracle_ref],
        "normalized_oracle_rows": [
            {
                "expected_status": "READY" if index % 2 == 0 else "NOT_OBSERVED",
                "oracle_ref_index": 0,
                "source_sha256": source_sha256,
            }
            for index, source_sha256 in enumerate(oracle_sources)
        ],
        "current_manifest_index_id": "gjfccmiv1:index:" + _sha(100),
        "current_manifest_source_sha256s": current_sources,
        "current_manifest_page_json_version_ids": pages,
        "current_trials": [
            {
                "source_sha256": source_sha256,
                "status": (
                    "READY"
                    if source_sha256 == oracle_sources[0]
                    else "NOT_OBSERVED"
                    if source_sha256 == oracle_sources[1]
                    else "UNRESOLVED"
                ),
            }
            for source_sha256 in current_sources
        ],
        "current_candidate_source_sha256s": [oracle_sources[0]],
        "current_replay_source_sha256s": oracle_sources,
        "current_selected_page_json_version_ids": list(reversed(pages)),
        "strict_compare": lambda oracle, current: {
            "disposition": (
                policy_v1.EXACT_HISTORICAL_COMPARISON
                if oracle["expected_status"] == current["status"]
                else "MISMATCH"
            ),
            "status": current["status"],
        },
    }


def test_strict_release_authenticates_oracle_and_exact_join(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    result = policy_v1.audit_historical_comparator_policy_v1(**kwargs)

    assert result["policy"] == policy_v1.STRICT_RELEASE
    assert result["disposition"] == policy_v1.EXACT_HISTORICAL_COMPARISON
    assert result["corpus_relation"]["overlap_count"] == 2
    assert result["corpus_relation"]["current_source_count"] == 3
    assert len(result["comparison_axis"]) == 2
    assert all(
        item["comparison"]["disposition"] == policy_v1.EXACT_HISTORICAL_COMPARISON
        for item in result["comparison_axis"]
    )


def test_disjoint_expansion_authenticates_oracle_without_fake_join(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    current_sources = [_sha(11), _sha(12), _sha(13)]
    kwargs.update(
        {
            "policy": policy_v1.DISJOINT_EXPANSION,
            "current_manifest_source_sha256s": current_sources,
            "current_trials": [
                {"source_sha256": source_sha256, "status": "UNRESOLVED"}
                for source_sha256 in current_sources
            ],
            "current_candidate_source_sha256s": [_sha(11)],
            "current_replay_source_sha256s": [_sha(11), _sha(12)],
            "strict_compare": None,
        }
    )

    result = policy_v1.audit_historical_comparator_policy_v1(**kwargs)

    assert result["disposition"] == policy_v1.NOT_APPLICABLE_DISJOINT_CORPUS
    assert result["corpus_relation"]["overlap_count"] == 0
    assert result["comparison_axis"] == []
    assert result["oracle_authentication"]["source_count"] == 2
    assert result["current_axis_validation"]["manifest_page_json_version_count"] == 3


def test_disjoint_expansion_does_not_pin_historical_page_denominator(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    current_sources = [_sha(11), _sha(12), _sha(13)]
    current_pages = [_page(index) for index in range(1, 14_946)]
    kwargs.update(
        {
            "policy": policy_v1.DISJOINT_EXPANSION,
            "current_manifest_source_sha256s": current_sources,
            "current_manifest_page_json_version_ids": current_pages,
            "current_trials": [
                {"source_sha256": source_sha256, "status": "UNRESOLVED"}
                for source_sha256 in current_sources
            ],
            "current_candidate_source_sha256s": [_sha(11)],
            "current_replay_source_sha256s": current_sources,
            "current_selected_page_json_version_ids": list(reversed(current_pages)),
            "strict_compare": None,
        }
    )

    result = policy_v1.audit_historical_comparator_policy_v1(**kwargs)

    assert result["current_axis_validation"]["manifest_page_json_version_count"] == 14_945
    assert result["current_axis_validation"]["selected_page_json_version_count"] == 14_945


@pytest.mark.parametrize(
    ("policy", "current_sources", "callback"),
    [
        (policy_v1.DISJOINT_EXPANSION, [_sha(1), _sha(11)], None),
        (policy_v1.DISJOINT_EXPANSION, [_sha(1), _sha(2)], None),
        (policy_v1.STRICT_RELEASE, [_sha(1), _sha(11)], lambda _old, _new: {}),
    ],
)
def test_partial_or_wrong_mode_oracle_overlap_is_rejected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    policy: str,
    current_sources: list[str],
    callback: object,
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    kwargs.update(
        {
            "policy": policy,
            "current_manifest_source_sha256s": current_sources,
            "current_trials": [
                {"source_sha256": source_sha256, "status": "READY"}
                for source_sha256 in current_sources
            ],
            "current_candidate_source_sha256s": [],
            "current_replay_source_sha256s": [],
            "strict_compare": callback,
        }
    )
    with pytest.raises(policy_v1.HistoricalComparatorPolicyV1Error):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


def test_strict_release_rejects_semantic_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    kwargs["current_trials"][0]["status"] = "UNRESOLVED"
    with pytest.raises(
        policy_v1.HistoricalComparatorPolicyV1Error,
        match="comparison is not exact",
    ):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


@pytest.mark.parametrize("tamper", ["sha256", "size_bytes", "format_version", "count"])
def test_oracle_byte_format_and_denominator_tamper_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tamper: str
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    reference = kwargs["pinned_oracle_refs"][0]
    if tamper == "sha256":
        reference["sha256"] = _sha(99)
    elif tamper == "size_bytes":
        reference["size_bytes"] += 1
    elif tamper == "format_version":
        reference["format_version"] = "FORGED"
    else:
        reference["expected_trial_count"] += 1
    with pytest.raises(policy_v1.HistoricalComparatorPolicyV1Error):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


def test_normalised_rows_must_exactly_bind_each_oracle_trial(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    kwargs["normalized_oracle_rows"][1]["source_sha256"] = _sha(19)
    with pytest.raises(
        policy_v1.HistoricalComparatorPolicyV1Error,
        match="do not bind",
    ):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


@pytest.mark.parametrize(
    "mutation",
    [
        "missing_trial",
        "duplicate_trial",
        "candidate_outside",
        "replay_outside",
        "missing_page",
        "duplicate_page",
        "extra_page",
        "bad_manifest_id",
    ],
)
def test_current_authenticated_axes_fail_closed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    if mutation == "missing_trial":
        kwargs["current_trials"].pop()
    elif mutation == "duplicate_trial":
        kwargs["current_trials"][1]["source_sha256"] = kwargs["current_trials"][0]["source_sha256"]
    elif mutation == "candidate_outside":
        kwargs["current_candidate_source_sha256s"] = [_sha(99)]
    elif mutation == "replay_outside":
        kwargs["current_replay_source_sha256s"] = [_sha(99)]
    elif mutation == "missing_page":
        kwargs["current_selected_page_json_version_ids"].pop()
    elif mutation == "duplicate_page":
        kwargs["current_selected_page_json_version_ids"][1] = kwargs[
            "current_selected_page_json_version_ids"
        ][0]
    elif mutation == "extra_page":
        kwargs["current_selected_page_json_version_ids"].append(_page(99))
    else:
        kwargs["current_manifest_index_id"] = "gjfccmiv1:index:not-a-digest"
    with pytest.raises(policy_v1.HistoricalComparatorPolicyV1Error):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


def test_multiple_oracles_require_globally_disjoint_source_axes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    second = _write_oracle(
        tmp_path,
        name="oracle-two.json",
        format_version="TEST_ORACLE_TWO_V1",
        source_sha256s=[_sha(2)],
    )
    kwargs["pinned_oracle_refs"].append(second)
    kwargs["normalized_oracle_rows"].append(
        {"expected_status": "READY", "oracle_ref_index": 1, "source_sha256": _sha(2)}
    )
    with pytest.raises(
        policy_v1.HistoricalComparatorPolicyV1Error,
        match="source axis is duplicate",
    ):
        policy_v1.audit_historical_comparator_policy_v1(**kwargs)


def test_inputs_are_not_mutated(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    kwargs = _fixture(tmp_path, monkeypatch)
    before = copy.deepcopy(kwargs)
    policy_v1.audit_historical_comparator_policy_v1(**kwargs)
    assert kwargs == before
