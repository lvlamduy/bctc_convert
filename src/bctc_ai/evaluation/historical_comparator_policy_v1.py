"""Authenticate historical comparators across release and expansion corpora.

Historical family runners originally assumed that every pinned oracle source
also occurred in the corpus being evaluated.  That is correct for a release
replay of the original corpus, but impossible for a deliberately disjoint
bank expansion.  This module makes that distinction explicit without turning
the historical oracle off: expansion mode still authenticates every oracle
byte and its complete source axis, then proves that the current corpus is
strictly disjoint.

Family-specific runners remain responsible for normalising the semantic
oracle rows and for performing their exact status/page/mapping comparison.
This module owns only immutable artifact authentication, corpus relation, and
the current manifest/trial/replay axes.
"""

from __future__ import annotations

import hashlib
import json
import os
import stat
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from bctc_ai.source_structure.contracts_v1 import (
    canonical_clone_v1,
    canonical_json_sha256_v1,
)

FORMAT_VERSION = "HISTORICAL_COMPARATOR_POLICY_AUDIT_V1"
STRICT_RELEASE = "STRICT_RELEASE"
DISJOINT_EXPANSION = "DISJOINT_EXPANSION"
EXACT_HISTORICAL_COMPARISON = "EXACT_HISTORICAL_COMPARISON"
NOT_APPLICABLE_DISJOINT_CORPUS = "NOT_APPLICABLE_DISJOINT_CORPUS"

_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_PINNED_REF_FIELDS = {
    "expected_trial_count",
    "format_version",
    "path",
    "sha256",
    "size_bytes",
}


class HistoricalComparatorPolicyV1Error(ValueError):
    """A pinned oracle or its release/expansion relation drifted."""


def _error(message: str) -> HistoricalComparatorPolicyV1Error:
    return HistoricalComparatorPolicyV1Error(message)


def _is_sha256(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value)
    )


def _is_manifest_index_id(value: object) -> bool:
    prefix = "gjfccmiv1:index:"
    return type(value) is str and value.startswith(prefix) and _is_sha256(value[len(prefix) :])


def _stable_read_project_file_v1(relative_path: str) -> bytes:
    relative = Path(relative_path)
    if (
        not relative_path
        or relative.is_absolute()
        or relative.parts in {(), (".",)}
        or any(part in {"", ".", ".."} for part in relative.parts)
    ):
        raise _error("pinned historical oracle path is not one bounded relative path")
    directory_flags = (
        os.O_RDONLY
        | getattr(os, "O_CLOEXEC", 0)
        | getattr(os, "O_DIRECTORY", 0)
        | getattr(os, "O_NOFOLLOW", 0)
    )
    file_flags = os.O_RDONLY | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0)
    current_descriptor = -1
    file_descriptor = -1
    try:
        current_descriptor = os.open(_PROJECT_ROOT, directory_flags)
        for part in relative.parts[:-1]:
            following = os.open(part, directory_flags, dir_fd=current_descriptor)
            os.close(current_descriptor)
            current_descriptor = following
        file_descriptor = os.open(relative.parts[-1], file_flags, dir_fd=current_descriptor)
        before = os.fstat(file_descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise _error("pinned historical oracle is not one regular file")
        chunks: list[bytes] = []
        while chunk := os.read(file_descriptor, 1 << 20):
            chunks.append(chunk)
        after = os.fstat(file_descriptor)
    except OSError as exc:
        raise _error("pinned historical oracle cannot be read without following links") from exc
    finally:
        if file_descriptor >= 0:
            os.close(file_descriptor)
        if current_descriptor >= 0:
            os.close(current_descriptor)
    identity = lambda value: (  # noqa: E731
        value.st_dev,
        value.st_ino,
        value.st_mode,
        value.st_size,
        value.st_mtime_ns,
        value.st_ctime_ns,
    )
    payload = b"".join(chunks)
    if identity(before) != identity(after) or len(payload) != before.st_size:
        raise _error("pinned historical oracle changed during stable read")
    return payload


def _oracle_trial_source_sha256_v1(trial: Mapping[str, Any]) -> str:
    candidates: list[str] = []
    for key in ("source_sha256", "source_pdf_sha256"):
        value = trial.get(key)
        if value is not None:
            candidates.append(value)
    for owner_key in ("source_pdf", "document_provenance", "bank_provenance"):
        owner = trial.get(owner_key)
        if type(owner) is not dict:
            continue
        for key in ("sha256", "source_sha256", "source_pdf_sha256"):
            value = owner.get(key)
            if value is not None:
                candidates.append(value)
        nested = owner.get("source_pdf")
        if type(nested) is dict:
            for key in ("sha256", "source_sha256"):
                value = nested.get(key)
                if value is not None:
                    candidates.append(value)
    if not candidates or any(not _is_sha256(value) for value in candidates):
        raise _error("historical oracle trial source identity is absent or invalid")
    unique = set(candidates)
    if len(unique) != 1:
        raise _error("historical oracle trial source identities disagree")
    return candidates[0]


def _authenticate_oracles_v1(
    pinned_oracle_refs: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[list[str]]]:
    if (
        type(pinned_oracle_refs) not in {list, tuple}
        or not pinned_oracle_refs
        or any(type(reference) is not dict for reference in pinned_oracle_refs)
    ):
        raise _error("pinned historical oracle references are absent or invalid")
    authenticated_refs: list[dict[str, Any]] = []
    source_axes: list[list[str]] = []
    paths: set[str] = set()
    digests: set[str] = set()
    all_sources: set[str] = set()
    for reference in pinned_oracle_refs:
        if set(reference) != _PINNED_REF_FIELDS:
            raise _error("pinned historical oracle reference fields drifted")
        path = reference.get("path")
        digest = reference.get("sha256")
        size_bytes = reference.get("size_bytes")
        format_version = reference.get("format_version")
        expected_trial_count = reference.get("expected_trial_count")
        if (
            type(path) is not str
            or path in paths
            or not _is_sha256(digest)
            or digest in digests
            or type(size_bytes) is not int
            or size_bytes <= 0
            or type(format_version) is not str
            or not format_version
            or type(expected_trial_count) is not int
            or expected_trial_count <= 0
        ):
            raise _error("pinned historical oracle reference is invalid or duplicate")
        payload = _stable_read_project_file_v1(path)
        if len(payload) != size_bytes or hashlib.sha256(payload).hexdigest() != digest:
            raise _error("pinned historical oracle bytes drifted")
        try:
            artifact = json.loads(payload)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise _error("pinned historical oracle JSON is invalid") from exc
        trials = artifact.get("trials") if type(artifact) is dict else None
        if (
            type(artifact) is not dict
            or artifact.get("format_version") != format_version
            or type(trials) is not list
            or len(trials) != expected_trial_count
            or any(type(trial) is not dict for trial in trials)
        ):
            raise _error("pinned historical oracle format or trial denominator drifted")
        source_axis = [_oracle_trial_source_sha256_v1(trial) for trial in trials]
        if len(set(source_axis)) != len(source_axis) or all_sources.intersection(source_axis):
            raise _error("pinned historical oracle source axis is duplicate")
        all_sources.update(source_axis)
        paths.add(path)
        digests.add(digest)
        authenticated_refs.append(canonical_clone_v1(reference))
        source_axes.append(source_axis)
    return authenticated_refs, source_axes


def _unique_sha_axis_v1(values: Sequence[str], *, name: str, allow_empty: bool) -> list[str]:
    if type(values) not in {list, tuple} or (not allow_empty and not values):
        raise _error(f"{name} is absent or invalid")
    result = list(values)
    if any(not _is_sha256(value) for value in result) or len(set(result)) != len(result):
        raise _error(f"{name} is invalid or duplicate")
    return result


def _unique_string_axis_v1(values: Sequence[str], *, name: str) -> list[str]:
    if type(values) not in {list, tuple} or not values:
        raise _error(f"{name} is absent or invalid")
    result = list(values)
    if any(type(value) is not str or not value for value in result) or len(set(result)) != len(
        result
    ):
        raise _error(f"{name} is invalid or duplicate")
    return result


def _current_trial_axis_v1(
    current_trials: Sequence[Mapping[str, Any]],
) -> tuple[list[str], dict[str, Mapping[str, Any]]]:
    if (
        type(current_trials) not in {list, tuple}
        or not current_trials
        or any(type(trial) is not dict for trial in current_trials)
    ):
        raise _error("current trial axis is absent or invalid")
    source_axis = [trial.get("source_sha256") for trial in current_trials]
    if any(not _is_sha256(value) for value in source_axis) or len(set(source_axis)) != len(
        source_axis
    ):
        raise _error("current trial source axis is invalid or duplicate")
    return source_axis, dict(zip(source_axis, current_trials, strict=True))


def _normalised_oracle_axis_v1(
    normalized_oracle_rows: Sequence[Mapping[str, Any]],
    *,
    oracle_source_axes: Sequence[Sequence[str]],
) -> list[dict[str, Any]]:
    if (
        type(normalized_oracle_rows) not in {list, tuple}
        or not normalized_oracle_rows
        or any(type(row) is not dict for row in normalized_oracle_rows)
    ):
        raise _error("normalised historical oracle row axis is absent or invalid")
    rows = [canonical_clone_v1(row) for row in normalized_oracle_rows]
    seen: set[tuple[int, str]] = set()
    grouped: list[list[str]] = [[] for _ in oracle_source_axes]
    for row in rows:
        reference_index = row.get("oracle_ref_index")
        source_sha256 = row.get("source_sha256")
        if (
            type(reference_index) is not int
            or reference_index < 0
            or reference_index >= len(oracle_source_axes)
            or not _is_sha256(source_sha256)
            or (reference_index, source_sha256) in seen
        ):
            raise _error("normalised historical oracle row provenance is invalid or duplicate")
        seen.add((reference_index, source_sha256))
        grouped[reference_index].append(source_sha256)
    for expected, actual in zip(oracle_source_axes, grouped, strict=True):
        if set(expected) != set(actual) or len(expected) != len(actual):
            raise _error("normalised historical oracle rows do not bind the artifact trial axis")
    return rows


def audit_historical_comparator_policy_v1(
    *,
    policy: str,
    pinned_oracle_refs: Sequence[Mapping[str, Any]],
    normalized_oracle_rows: Sequence[Mapping[str, Any]],
    current_manifest_index_id: str,
    current_manifest_source_sha256s: Sequence[str],
    current_manifest_page_json_version_ids: Sequence[str],
    current_trials: Sequence[Mapping[str, Any]],
    current_candidate_source_sha256s: Sequence[str],
    current_replay_source_sha256s: Sequence[str],
    current_selected_page_json_version_ids: Sequence[str],
    strict_compare: Callable[[Mapping[str, Any], Mapping[str, Any]], Mapping[str, Any]] | None,
) -> dict[str, Any]:
    """Authenticate either an exact historical replay or a disjoint expansion.

    ``normalized_oracle_rows`` must contain exactly one row per authenticated
    oracle trial and include ``oracle_ref_index`` plus ``source_sha256``.
    Family-specific fields may be added freely and are passed unchanged to
    ``strict_compare`` in release mode.
    """

    if policy not in {STRICT_RELEASE, DISJOINT_EXPANSION}:
        raise _error("historical comparator policy is undeclared")
    if not _is_manifest_index_id(current_manifest_index_id):
        raise _error("current manifest index identity is absent or invalid")

    authenticated_refs, oracle_source_axes = _authenticate_oracles_v1(pinned_oracle_refs)
    oracle_rows = _normalised_oracle_axis_v1(
        normalized_oracle_rows, oracle_source_axes=oracle_source_axes
    )
    oracle_sources = [source for axis in oracle_source_axes for source in axis]
    manifest_sources = _unique_sha_axis_v1(
        current_manifest_source_sha256s,
        name="current manifest source axis",
        allow_empty=False,
    )
    trial_sources, trial_by_source = _current_trial_axis_v1(current_trials)
    if set(manifest_sources) != set(trial_sources) or len(manifest_sources) != len(trial_sources):
        raise _error("current trial source axis is not the exact manifest source frontier")
    candidate_sources = _unique_sha_axis_v1(
        current_candidate_source_sha256s,
        name="current candidate source axis",
        allow_empty=True,
    )
    replay_sources = _unique_sha_axis_v1(
        current_replay_source_sha256s,
        name="current replay source axis",
        allow_empty=True,
    )
    if not set(candidate_sources).issubset(trial_by_source) or not set(replay_sources).issubset(
        trial_by_source
    ):
        raise _error("current candidate or replay source lies outside the authenticated trials")

    manifest_page_ids = _unique_string_axis_v1(
        current_manifest_page_json_version_ids,
        name="current manifest page-JSON version axis",
    )
    selected_page_ids = _unique_string_axis_v1(
        current_selected_page_json_version_ids,
        name="current selected page-JSON version axis",
    )
    if set(manifest_page_ids) != set(selected_page_ids) or len(manifest_page_ids) != len(
        selected_page_ids
    ):
        raise _error("selected page-JSON version axis is not the exact manifest frontier")

    overlap = sorted(set(oracle_sources).intersection(manifest_sources))
    if 0 < len(overlap) < len(oracle_sources):
        raise _error("historical oracle and current corpus overlap only partially")

    comparison_axis: list[dict[str, Any]] = []
    if policy == STRICT_RELEASE:
        if len(overlap) != len(oracle_sources) or strict_compare is None:
            raise _error("strict historical release requires every oracle source and comparator")
        for row in oracle_rows:
            source_sha256 = row["source_sha256"]
            try:
                comparison = strict_compare(row, trial_by_source[source_sha256])
            except (KeyError, TypeError, ValueError) as exc:
                raise _error("strict historical comparison could not be replayed") from exc
            if (
                type(comparison) is not dict
                or comparison.get("disposition") != EXACT_HISTORICAL_COMPARISON
            ):
                raise _error("strict historical comparison is not exact")
            comparison_axis.append(
                {
                    "comparison": canonical_clone_v1(comparison),
                    "oracle_ref_index": row["oracle_ref_index"],
                    "source_sha256": source_sha256,
                }
            )
        disposition = EXACT_HISTORICAL_COMPARISON
        expected_relation = "ORACLE_SOURCES_ARE_AN_EXACT_JOINABLE_SUBSET_OF_CURRENT_CORPUS"
    else:
        if overlap or strict_compare is not None:
            raise _error(
                "disjoint expansion requires zero oracle overlap and no comparator callback"
            )
        disposition = NOT_APPLICABLE_DISJOINT_CORPUS
        expected_relation = "ORACLE_AND_CURRENT_CORPUS_SOURCE_AXES_ARE_DISJOINT"

    sorted_oracle_sources = sorted(oracle_sources)
    sorted_manifest_sources = sorted(manifest_sources)
    return {
        "comparison_axis": comparison_axis,
        "corpus_relation": {
            "current_source_count": len(manifest_sources),
            "expected_relation": expected_relation,
            "oracle_source_count": len(oracle_sources),
            "ordered_current_source_axis_sha256": canonical_json_sha256_v1(sorted_manifest_sources),
            "overlap_count": len(overlap),
            "overlap_source_sha256s": overlap,
        },
        "current_axis_validation": {
            "candidate_source_count": len(candidate_sources),
            "manifest_document_count": len(manifest_sources),
            "manifest_index_id": current_manifest_index_id,
            "manifest_page_json_version_count": len(manifest_page_ids),
            "ordered_candidate_source_axis_sha256": canonical_json_sha256_v1(
                sorted(candidate_sources)
            ),
            "ordered_replay_source_axis_sha256": canonical_json_sha256_v1(sorted(replay_sources)),
            "ordered_selected_page_json_version_axis_sha256": canonical_json_sha256_v1(
                sorted(selected_page_ids)
            ),
            "ordered_trial_source_axis_sha256": canonical_json_sha256_v1(sorted(trial_sources)),
            "replay_source_count": len(replay_sources),
            "selected_page_json_version_count": len(selected_page_ids),
            "trial_source_count": len(trial_sources),
        },
        "disposition": disposition,
        "format_version": FORMAT_VERSION,
        "oracle_authentication": {
            "artifact_count": len(authenticated_refs),
            "ordered_source_sha256_axis_sha256": canonical_json_sha256_v1(sorted_oracle_sources),
            "refs": authenticated_refs,
            "row_count": len(oracle_rows),
            "source_count": len(oracle_sources),
        },
        "policy": policy,
    }


__all__ = [
    "DISJOINT_EXPANSION",
    "EXACT_HISTORICAL_COMPARISON",
    "FORMAT_VERSION",
    "HistoricalComparatorPolicyV1Error",
    "NOT_APPLICABLE_DISJOINT_CORPUS",
    "STRICT_RELEASE",
    "audit_historical_comparator_policy_v1",
]
