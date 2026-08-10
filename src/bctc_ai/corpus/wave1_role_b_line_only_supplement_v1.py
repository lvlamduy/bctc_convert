from __future__ import annotations

import fcntl
import json
import os
import re
import shutil
import stat
import subprocess
from collections import Counter
from collections.abc import Iterator, Mapping, Sequence
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from bctc_ai.core.hashing import sha256_bytes
from bctc_ai.corpus import wave1_role_b_full_reader_v2 as full_v2
from bctc_ai.corpus import wave1_role_b_sentinel as sentinel
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WaveOneRoleBWordBoxNormalizationError,
    normalize_ppocrv6_word_boxes,
)
from bctc_ai.ocr.ppocrv6_page_session import validate_ppocrv6_payload
from bctc_ai.rendering.page_reader import transform_pixel_polygon_to_unrotated_mpt


class WaveOneRoleBLineOnlySupplementError(RuntimeError):
    """The authenticated post-V2 line-only supplement cannot proceed."""


POLICY_RELATIVE_PATH = Path("config/corpus/bank-corpus-wave-1-role-b-line-only-supplement-v1.yaml")
POLICY_SHA256 = "2bd92441d79c3eb43a86f53023c7fb24aeb5e5f1f98906191496952a8a95e86b"
POLICY_SIZE_BYTES = 5_205
OUTPUT_RELATIVE_ROOT = Path(
    "output/development/bank-corpus-wave-1-role-b-line-only-supplement-v1/full-v1"
)
UPSTREAM_OUTPUT_RELATIVE_ROOT = full_v2.OUTPUT_RELATIVE_ROOT
CONTROL_FILENAME = "line-only-execution-control.json"
AGGREGATE_FILENAME = "line-only-supplement-aggregate.json"
LEASE_FILENAME = "line-only-execution.lock"

MODULE_RELATIVE_PATH = Path("src/bctc_ai/corpus/wave1_role_b_line_only_supplement_v1.py")
CLI_RELATIVE_PATH = Path("scripts/corpus/run_wave1_role_b_line_only_supplement_v1.py")
LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS = tuple(
    dict.fromkeys(
        (
            *full_v2.FULL_READER_IMPLEMENTATION_RELATIVE_PATHS,
            POLICY_RELATIVE_PATH,
            MODULE_RELATIVE_PATH,
            CLI_RELATIVE_PATH,
        )
    )
)

_SHA256_CHARACTERS = frozenset("0123456789abcdef")
_TERMINAL_STATUS = "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
_FAILURE_REASON = "BOUNDED_WORD_BOX_NORMALIZATION_INVARIANT_FAILED"
_OCR_ROUTE = "DOMINANT_RASTER_OCR"
_PAGE_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_PAGE_EVIDENCE_V1"
_LINE_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_OBSERVATION_V1"
_CHECKPOINT_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_CHECKPOINT_V1"
_CONTROL_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_SUPPLEMENT_CONTROL_V1"
_AGGREGATE_FORMAT = "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_SUPPLEMENT_V1"
_ACCEPTED_DISPOSITION = "LINE_ONLY_EVIDENCE_AVAILABLE_FROM_TERMINAL_WORD_BOX_GEOMETRY"
_REJECTED_DISPOSITION = "NO_LINE_ONLY_EVIDENCE_AVAILABLE_NO_NONEMPTY_VALID_LINE_TEXT"
_CLAIM_BOUNDARY = (
    "AUTHENTICATED_PPOCRV6_LINE_TEXT_SCORE_AND_LINE_GEOMETRY_ONLY_FROM_"
    "TERMINAL_WORD_BOX_GEOMETRY_PAGE"
)
_CHECKPOINT_NAME = re.compile(r"^(?P<generation>[0-9]{4})-(?P<request>[0-9a-f]{64})\.json$")
_CHECKPOINT_TEMP = re.compile(r"^\.(?P<final>[0-9]{4}-[0-9a-f]{64}\.json)\.[0-9a-f]{32}\.tmp$")
_GIT_OBJECT_ID = re.compile(r"^[0-9a-f]{40}$")
_ROOT_PUBLICATION_TEMP = re.compile(
    rf"^\.(?P<final>{re.escape(CONTROL_FILENAME)}|{re.escape(AGGREGATE_FILENAME)})\."
    r"(?P<nonce>[0-9a-f]{32})\.tmp$"
)

_COORDINATE_KEYS = {
    "matrix_convention",
    "pixel_coordinate_system",
    "displayed_coordinate_system",
    "canonical_coordinate_system",
    "canonical_origin",
    "pixel_dimensions",
    "displayed_dimensions_mpt",
    "unrotated_dimensions_mpt",
    "pdf_rotation_degrees",
    "pixel_to_displayed_mpt",
    "displayed_mpt_to_unrotated_mpt",
    "pixel_to_unrotated_mpt",
    "unrotated_mpt_to_pixel",
}

_UPSTREAM_BACKEND_KEYS = {
    "format_version",
    "claim_boundary",
    "request_sha256",
    "request",
    "provider_identity_sha256",
    "render_ref",
    "raw_provider_payload",
    "word_box_normalization_ledger",
    "normalization_failure",
}
_UPSTREAM_RESULT_KEYS = {
    "format_version",
    "status",
    "claim_boundary",
    "request_sha256",
    "request",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "provider_identity_sha256",
    "render_runtime_identity_sha256",
    "input_render_ref",
    "backend_payload_ref",
    "normalization_failure",
    "coordinate_authority",
    "lines",
    "words",
    "metrics",
    "ocr_fallback_used",
    "source_blank_claimed",
    "safety",
}
_UPSTREAM_PAGE_RECORD_KEYS = {
    "format_version",
    "request_ordinal",
    "document_id",
    "source_sha256",
    "source_size_bytes",
    "physical_page",
    "route",
    "request_sha256",
    "request",
    "status",
    "origin",
    "render_ref",
    "backend_payload_ref",
    "result_ref",
    "line_count",
    "word_token_count",
    "unresolved",
    "quarantined_span_count",
    "word_box_correction_count",
    "word_box_corrected_edge_count",
    "statement_classification_count",
    "table_classification_count",
    "row_reconstruction_count",
    "cell_interpretation_count",
    "absence_declaration_count",
}


@dataclass(frozen=True)
class FinalizedV2Authority:
    aggregate: dict[str, Any]
    control: dict[str, Any]
    aggregate_payload: bytes
    control_payload: bytes
    aggregate_identity: tuple[int, int, int, int, int, int]
    control_identity: tuple[int, int, int, int, int, int]
    terminal_object_identities: tuple[tuple[str, tuple[int, int, int, int, int, int]], ...]


def _canonical_bytes(value: Any) -> bytes:
    try:
        return (
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
            + "\n"
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        raise WaveOneRoleBLineOnlySupplementError("value is not finite canonical JSON") from error


def _canonical_sha256(value: Any) -> str:
    return sha256_bytes(_canonical_bytes(value))


def _same_typed_json(left: Any, right: Any) -> bool:
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return set(left) == set(right) and all(
            _same_typed_json(left[key], right[key]) for key in left
        )
    if isinstance(left, list):
        return len(left) == len(right) and all(
            _same_typed_json(a, b) for a, b in zip(left, right, strict=True)
        )
    if isinstance(left, float):
        return isfinite(left) and isfinite(right) and left.hex() == right.hex()
    return left == right


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and len(value) == 64 and set(value) <= _SHA256_CHARACTERS


def _json_object(payload: bytes, label: str) -> dict[str, Any]:
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is not canonical JSON") from error
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} canonical bytes drifted")
    return value


def _stat_identity(identity: os.stat_result) -> tuple[int, int, int, int, int, int]:
    return (
        identity.st_dev,
        identity.st_ino,
        identity.st_size,
        identity.st_mtime_ns,
        stat.S_IMODE(identity.st_mode),
        identity.st_nlink,
    )


def _read_immutable_relative(
    project_root: Path,
    relative: Path,
    *,
    label: str,
    mode: int = 0o444,
) -> tuple[bytes, os.stat_result]:
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} path is unsafe")
    try:
        with sentinel._held_directory(  # noqa: SLF001 - authenticated nofollow substrate
            project_root, relative.parent, create=False
        ) as (_directory, directory_fd):
            payload, identity = sentinel._hash_open_at(directory_fd, relative.name)  # noqa: SLF001
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} could not be read safely") from error
    if (
        not stat.S_ISREG(identity.st_mode)
        or stat.S_IMODE(identity.st_mode) != mode
        or identity.st_nlink != 1
    ):
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is not immutable")
    return payload, identity


def _read_stable_project_file(project_root: Path, relative: Path, *, label: str) -> bytes:
    if relative.is_absolute() or ".." in relative.parts or not relative.name:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} path is unsafe")
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, relative.parent, create=False
        ) as (_directory, directory_fd):
            payload, identity = sentinel._hash_open_at(directory_fd, relative.name)  # noqa: SLF001
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} could not be read safely") from error
    if not stat.S_ISREG(identity.st_mode) or identity.st_nlink != 1:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} identity is unsafe")
    return payload


def _load_policy(project_root: Path) -> dict[str, Any]:
    payload = _read_stable_project_file(project_root, POLICY_RELATIVE_PATH, label="policy")
    if len(payload) != POLICY_SIZE_BYTES or sha256_bytes(payload) != POLICY_SHA256:
        raise WaveOneRoleBLineOnlySupplementError("line-only policy byte identity drifted")
    try:
        policy = yaml.safe_load(payload)
    except yaml.YAMLError as error:
        raise WaveOneRoleBLineOnlySupplementError("line-only policy YAML is invalid") from error
    expected_sections = {
        "format_version",
        "status",
        "upstream",
        "terminal_denominator",
        "projection",
        "quarantine",
        "execution",
        "aggregate",
        "safety",
        "forbidden_inputs",
    }
    if not isinstance(policy, dict) or set(policy) != expected_sections:
        raise WaveOneRoleBLineOnlySupplementError("line-only policy sections drifted")
    exact_scalars = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_LINE_ONLY_SUPPLEMENT_POLICY_V1",
        "status": "LOCKED_ADD_ONLY_POST_V2_LINE_ONLY_SUPPLEMENT_POLICY",
    }
    if any(
        type(policy.get(key)) is not type(value) or policy.get(key) != value
        for key, value in exact_scalars.items()
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only policy identity drifted")
    for section in (
        "upstream",
        "terminal_denominator",
        "projection",
        "quarantine",
        "execution",
        "aggregate",
        "safety",
    ):
        if not isinstance(policy[section], dict):
            raise WaveOneRoleBLineOnlySupplementError(f"policy section is not an object: {section}")
    if (
        policy["upstream"].get("output_root") != UPSTREAM_OUTPUT_RELATIVE_ROOT.as_posix()
        or policy["upstream"].get("control_identity_sha256")
        != "5f4f00d40900be2765b6f873b268cd09c28026245157d2bdb0b293eb24a64be1"
        or policy["upstream"].get("control_artifact_sha256")
        != "198bc717b4cffda605bf598b83cd1c7ca391f4969e5d5ae26a0e8687cd07d440"
        or type(policy["upstream"].get("control_artifact_size_bytes")) is not int
        or policy["upstream"]["control_artifact_size_bytes"] != 4_608_592
        or policy["upstream"].get("sealed_plan_sha256") != full_v2.SEALED_PLAN_SHA256
        or type(policy["upstream"].get("sealed_plan_size_bytes")) is not int
        or policy["upstream"]["sealed_plan_size_bytes"] != full_v2.SEALED_PLAN_SIZE_BYTES
        or policy["terminal_denominator"].get("upstream_status") != _TERMINAL_STATUS
        or policy["terminal_denominator"].get("failure_reason") != _FAILURE_REASON
        or policy["projection"].get("page_format") != _PAGE_FORMAT
        or policy["projection"].get("claim_boundary") != _CLAIM_BOUNDARY
        or policy["projection"].get("line_eligibility_rule")
        != "EXACT_STRING_LENGTH_GREATER_THAN_ZERO_NO_TRIM"
        or policy["projection"].get("mixed_page_filtering")
        != "EMIT_ONLY_ELIGIBLE_LINES_PRESERVE_ORIGINAL_LINE_INDEX"
        or policy["projection"].get("excluded_empty_line_axis_metric")
        != "excluded_empty_line_axis_count"
        or policy["projection"].get("line_accounting_identity")
        != "VALIDATED_EQUALS_ACCEPTED_PLUS_EXCLUDED_EMPTY"
        or policy["execution"].get("output_root") != OUTPUT_RELATIVE_ROOT.as_posix()
        or policy["aggregate"].get("format_version") != _AGGREGATE_FORMAT
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only policy contract drifted")
    if not isinstance(policy["forbidden_inputs"], list) or any(
        not isinstance(value, str) for value in policy["forbidden_inputs"]
    ):
        raise WaveOneRoleBLineOnlySupplementError("policy forbidden-input list drifted")
    return policy


def _git_output(project_root: Path, arguments: Sequence[str], label: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=project_root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise WaveOneRoleBLineOnlySupplementError(f"git {label} failed")
    return result.stdout.strip()


def _git_blob(project_root: Path, commit: str, relative: str) -> bytes:
    if _GIT_OBJECT_ID.fullmatch(commit) is None:
        raise WaveOneRoleBLineOnlySupplementError("historical commit identity is malformed")
    result = subprocess.run(
        ["git", "show", "--no-ext-diff", f"{commit}:{relative}"],
        cwd=project_root,
        check=False,
        capture_output=True,
    )
    if result.returncode:
        raise WaveOneRoleBLineOnlySupplementError(
            f"historical line-only implementation is absent: {relative}"
        )
    return result.stdout


def _executor_identity(project_root: Path, *, require_clean: bool) -> dict[str, Any]:
    commit = _git_output(project_root, ["rev-parse", "HEAD"], "commit lookup")
    tree = _git_output(project_root, ["rev-parse", "HEAD^{tree}"], "tree lookup")
    branch = _git_output(project_root, ["rev-parse", "--abbrev-ref", "HEAD"], "branch lookup")
    if (
        _GIT_OBJECT_ID.fullmatch(commit) is None
        or _GIT_OBJECT_ID.fullmatch(tree) is None
        or not branch
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only producer Git identity is malformed")
    status_output = _git_output(project_root, ["status", "--porcelain=v1"], "status lookup")
    if require_clean and status_output:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only producer requires a clean committed worktree"
        )
    records = []
    for relative in LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS:
        historical = _git_blob(project_root, commit, relative.as_posix())
        current = _read_stable_project_file(
            project_root, relative, label="line-only implementation"
        )
        if current != historical:
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only implementation differs from producer commit"
            )
        records.append(
            {
                "phase": "READ",
                "kind": "IMPLEMENTATION",
                "path": relative.as_posix(),
                "sha256": sha256_bytes(historical),
                "size_bytes": len(historical),
            }
        )
    return {
        "git": {
            "commit": commit,
            "tree": tree,
            "branch": branch,
            "dirty": False,
        },
        "implementation_ledger": {
            "records": records,
            "sha256": _canonical_sha256(records),
        },
    }


def _validate_published_executor(project_root: Path, control: dict[str, Any]) -> None:
    git = control.get("executor_git")
    ledger = control.get("executor_implementation_ledger")
    if (
        not isinstance(git, dict)
        or set(git) != {"commit", "tree", "branch", "dirty"}
        or git.get("dirty") is not False
        or not isinstance(git.get("commit"), str)
        or _GIT_OBJECT_ID.fullmatch(git["commit"]) is None
        or not isinstance(git.get("tree"), str)
        or _GIT_OBJECT_ID.fullmatch(git["tree"]) is None
        or not isinstance(git.get("branch"), str)
        or not git["branch"]
        or not isinstance(ledger, dict)
        or set(ledger) != {"records", "sha256"}
        or not isinstance(ledger.get("records"), list)
        or ledger.get("sha256") != _canonical_sha256(ledger["records"])
    ):
        raise WaveOneRoleBLineOnlySupplementError("published line-only executor drifted")
    producer_tree = _git_output(
        project_root,
        ["rev-parse", "--verify", f"{git['commit']}^{{tree}}"],
        "producer tree lookup",
    )
    if producer_tree != git["tree"]:
        raise WaveOneRoleBLineOnlySupplementError("published producer tree drifted")
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", git["commit"], "HEAD"],
        cwd=project_root,
        check=False,
    )
    if ancestor.returncode:
        raise WaveOneRoleBLineOnlySupplementError("line-only producer commit is not an ancestor")
    records = ledger["records"]
    expected_paths = {path.as_posix() for path in LINE_ONLY_IMPLEMENTATION_RELATIVE_PATHS}
    if (
        len(records) != len(expected_paths)
        or {record.get("path") for record in records if isinstance(record, dict)} != expected_paths
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only ledger path set drifted")
    for record in records:
        if (
            not isinstance(record, dict)
            or set(record) != {"phase", "kind", "path", "sha256", "size_bytes"}
            or record["phase"] != "READ"
            or record["kind"] != "IMPLEMENTATION"
            or not _is_sha256(record["sha256"])
            or type(record["size_bytes"]) is not int
            or record["size_bytes"] < 0
        ):
            raise WaveOneRoleBLineOnlySupplementError("line-only ledger record drifted")
        historical = _git_blob(project_root, git["commit"], record["path"])
        current = _read_stable_project_file(
            project_root, Path(record["path"]), label="current line-only implementation"
        )
        if (
            len(historical) != record["size_bytes"]
            or sha256_bytes(historical) != record["sha256"]
            or current != historical
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only implementation historical replay drifted"
            )


def _read_upstream_object_with_identity(
    project_root: Path, reference: Mapping[str, Any], suffix: str
) -> tuple[bytes, os.stat_result]:
    if suffix != ".json" or not isinstance(reference, Mapping):
        raise WaveOneRoleBLineOnlySupplementError("upstream object reference is malformed")
    if set(reference) != {"path", "sha256", "size_bytes"}:
        raise WaveOneRoleBLineOnlySupplementError("upstream object reference fields drifted")
    digest = reference.get("sha256")
    size = reference.get("size_bytes")
    expected_path = f"objects/sha256/{str(digest)[:2]}/{digest}{suffix}"
    if (
        not _is_sha256(digest)
        or type(size) is not int
        or size < 0
        or reference.get("path") != expected_path
    ):
        raise WaveOneRoleBLineOnlySupplementError("upstream object reference identity drifted")
    payload, identity = _read_immutable_relative(
        project_root,
        UPSTREAM_OUTPUT_RELATIVE_ROOT / expected_path,
        label="upstream content-addressed object",
    )
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise WaveOneRoleBLineOnlySupplementError("upstream object content drifted")
    return payload, identity


def _read_upstream_object(project_root: Path, reference: Mapping[str, Any], suffix: str) -> bytes:
    payload, _identity = _read_upstream_object_with_identity(project_root, reference, suffix)
    return payload


def _terminal_records(aggregate: dict[str, Any]) -> list[dict[str, Any]]:
    records = aggregate.get("page_records")
    accounting = aggregate.get("accounting")
    normalization = aggregate.get("word_box_normalization_accounting")
    if (
        not isinstance(records, list)
        or not isinstance(accounting, dict)
        or not isinstance(normalization, dict)
    ):
        raise WaveOneRoleBLineOnlySupplementError("upstream aggregate accounting is absent")
    selected = []
    seen = set()
    for record in records:
        if not isinstance(record, dict):
            raise WaveOneRoleBLineOnlySupplementError("upstream page record is malformed")
        request_sha = record.get("request_sha256")
        if not _is_sha256(request_sha) or request_sha in seen:
            raise WaveOneRoleBLineOnlySupplementError("upstream request identity is duplicated")
        seen.add(request_sha)
        if record.get("status") == _TERMINAL_STATUS:
            if (
                set(record) != _UPSTREAM_PAGE_RECORD_KEYS
                or record.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_RECORD_V1"
                or record.get("route") != _OCR_ROUTE
                or record.get("unresolved") is not True
                or record.get("origin") != "PINNED_PPOCRV6_FULL_READER"
                or type(record.get("request_ordinal")) is not int
                or not 1 <= record["request_ordinal"] <= 1_449
                or not isinstance(record.get("document_id"), str)
                or record["document_id"] != f"sha256:{record.get('source_sha256')}"
                or not _is_sha256(record.get("source_sha256"))
                or type(record.get("source_size_bytes")) is not int
                or record["source_size_bytes"] <= 0
                or type(record.get("physical_page")) is not int
                or record["physical_page"] <= 0
                or not isinstance(record.get("request"), dict)
                or _canonical_sha256(record["request"]) != request_sha
                or type(record.get("line_count")) is not int
                or record["line_count"] != 0
                or type(record.get("word_token_count")) is not int
                or record["word_token_count"] != 0
                or any(
                    type(record.get(key)) is not int or record[key] != 0
                    for key in (
                        "quarantined_span_count",
                        "word_box_correction_count",
                        "word_box_corrected_edge_count",
                        "statement_classification_count",
                        "table_classification_count",
                        "row_reconstruction_count",
                        "cell_interpretation_count",
                        "absence_declaration_count",
                    )
                )
            ):
                raise WaveOneRoleBLineOnlySupplementError(
                    "upstream terminal page record contract drifted"
                )
            selected.append(record)
    selected.sort(key=lambda item: item["request_ordinal"])
    outcomes = accounting.get("outcome_counts")
    if not isinstance(outcomes, dict):
        raise WaveOneRoleBLineOnlySupplementError("upstream outcome accounting is absent")
    expected = outcomes.get(_TERMINAL_STATUS, 0)
    if (
        type(expected) is not int
        or expected != len(selected)
        or type(normalization.get("unresolved_geometry_page_count")) is not int
        or normalization["unresolved_geometry_page_count"] != len(selected)
        or len(records) != 1_449
        or type(accounting.get("request_count")) is not int
        or accounting["request_count"] != 1_449
    ):
        raise WaveOneRoleBLineOnlySupplementError(
            "upstream terminal denominator does not reconcile"
        )
    return selected


def _authenticate_finalized_v2(project_root: Path, *, model_cache: Path) -> FinalizedV2Authority:
    try:
        replay = full_v2.verify_authenticated_full_reader(project_root, model_cache=model_cache)
    except RuntimeError as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "finalized V2 read-only verifier did not pass"
        ) from error
    aggregate_payload, aggregate_stat = _read_immutable_relative(
        project_root,
        UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json",
        label="finalized V2 aggregate",
    )
    control_payload, control_stat = _read_immutable_relative(
        project_root,
        UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-execution-control.json",
        label="published V2 control",
    )
    aggregate = _json_object(aggregate_payload, "finalized V2 aggregate")
    control = _json_object(control_payload, "published V2 control")
    if not _same_typed_json(aggregate, replay):
        raise WaveOneRoleBLineOnlySupplementError(
            "published V2 aggregate differs from verified replay"
        )
    identity = aggregate.get("aggregate_identity_sha256")
    if (
        aggregate.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V1"
        or aggregate.get("status")
        not in {
            "COMPLETE_AUTHENTICATED_WAVE_1_PAGE_READS",
            "COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS",
        }
        or not _is_sha256(identity)
        or _canonical_sha256(
            {key: value for key, value in aggregate.items() if key != "aggregate_identity_sha256"}
        )
        != identity
        or control.get("control_identity_sha256")
        != "5f4f00d40900be2765b6f873b268cd09c28026245157d2bdb0b293eb24a64be1"
        or sha256_bytes(control_payload)
        != "198bc717b4cffda605bf598b83cd1c7ca391f4969e5d5ae26a0e8687cd07d440"
        or len(control_payload) != 4_608_592
        or aggregate.get("control", {}).get("identity_sha256") != control["control_identity_sha256"]
        or aggregate.get("sealed_plan", {}).get("sha256") != full_v2.SEALED_PLAN_SHA256
    ):
        raise WaveOneRoleBLineOnlySupplementError("finalized V2 authority drifted")
    terminal_object_identities = []
    for record in _terminal_records(aggregate):
        for key in ("backend_payload_ref", "result_ref"):
            _payload, object_stat = _read_upstream_object_with_identity(
                project_root, record[key], ".json"
            )
            terminal_object_identities.append((record[key]["path"], _stat_identity(object_stat)))
    return FinalizedV2Authority(
        aggregate=aggregate,
        control=control,
        aggregate_payload=aggregate_payload,
        control_payload=control_payload,
        aggregate_identity=_stat_identity(aggregate_stat),
        control_identity=_stat_identity(control_stat),
        terminal_object_identities=tuple(terminal_object_identities),
    )


def _recheck_upstream_authority(project_root: Path, authority: FinalizedV2Authority) -> None:
    aggregate_payload, aggregate_stat = _read_immutable_relative(
        project_root,
        UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-aggregate.json",
        label="finalized V2 aggregate recheck",
    )
    control_payload, control_stat = _read_immutable_relative(
        project_root,
        UPSTREAM_OUTPUT_RELATIVE_ROOT / "full-reader-execution-control.json",
        label="published V2 control recheck",
    )
    if (
        aggregate_payload != authority.aggregate_payload
        or control_payload != authority.control_payload
        or _stat_identity(aggregate_stat) != authority.aggregate_identity
        or _stat_identity(control_stat) != authority.control_identity
    ):
        raise WaveOneRoleBLineOnlySupplementError(
            "upstream V2 authority changed during line-only replay"
        )
    expected_identities = dict(authority.terminal_object_identities)
    terminal_records = _terminal_records(authority.aggregate)
    if len(expected_identities) != 2 * len(terminal_records):
        raise WaveOneRoleBLineOnlySupplementError(
            "upstream terminal object identity snapshot is incomplete"
        )
    for record in terminal_records:
        for key in ("backend_payload_ref", "result_ref"):
            _payload, observed = _read_upstream_object_with_identity(
                project_root, record[key], ".json"
            )
            if _stat_identity(observed) != expected_identities.get(record[key]["path"]):
                raise WaveOneRoleBLineOnlySupplementError(
                    "upstream terminal object topology changed during line-only replay"
                )


def _finite_number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not isfinite(value):
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is not a finite number")
    return value


def _validate_rational_matrix(value: Any, label: str) -> tuple[tuple[Any, ...], ...]:
    if (
        not isinstance(value, list)
        or len(value) != 3
        or any(not isinstance(row, list) or len(row) != 3 for row in value)
    ):
        raise WaveOneRoleBLineOnlySupplementError(f"{label} matrix shape drifted")
    restored = []
    for row in value:
        restored_row = []
        for coefficient in row:
            if (
                not isinstance(coefficient, dict)
                or set(coefficient) != {"numerator", "denominator"}
                or type(coefficient["numerator"]) is not int
                or type(coefficient["denominator"]) is not int
                or coefficient["denominator"] <= 0
            ):
                raise WaveOneRoleBLineOnlySupplementError(f"{label} rational coefficient drifted")
            restored_row.append((coefficient["numerator"], coefficient["denominator"]))
        restored.append(tuple(restored_row))
    return tuple(restored)


def _restore_coordinate_authority(public: Any) -> dict[str, Any]:
    if not isinstance(public, dict) or set(public) != _COORDINATE_KEYS:
        raise WaveOneRoleBLineOnlySupplementError("coordinate authority fields drifted")
    expected_strings = {
        "matrix_convention": "COLUMN_VECTOR_3X3_RATIONAL",
        "pixel_coordinate_system": "DISPLAYED_PAGE_RASTER_PIXELS_TOP_LEFT",
        "displayed_coordinate_system": "DISPLAYED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_coordinate_system": "UNROTATED_PDF_MILLI_POINTS_TOP_LEFT",
        "canonical_origin": "UNROTATED_CROP_BOX_TOP_LEFT_RELATIVE",
    }
    if any(public.get(key) != value for key, value in expected_strings.items()):
        raise WaveOneRoleBLineOnlySupplementError("coordinate authority system drifted")
    for key in (
        "pixel_dimensions",
        "displayed_dimensions_mpt",
        "unrotated_dimensions_mpt",
    ):
        dimensions = public.get(key)
        if (
            not isinstance(dimensions, list)
            or len(dimensions) != 2
            or any(type(value) is not int or value <= 0 for value in dimensions)
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                f"coordinate authority dimensions drifted: {key}"
            )
    if type(public.get("pdf_rotation_degrees")) is not int or public[
        "pdf_rotation_degrees"
    ] not in {0, 90, 180, 270}:
        raise WaveOneRoleBLineOnlySupplementError("coordinate authority rotation drifted")
    authority = deepcopy(public)
    for key in (
        "pixel_to_displayed_mpt",
        "displayed_mpt_to_unrotated_mpt",
        "pixel_to_unrotated_mpt",
        "unrotated_mpt_to_pixel",
    ):
        _validate_rational_matrix(public[key], key)
    authority["_pixel_to_unrotated_matrix"] = _validate_rational_matrix(
        public["pixel_to_unrotated_mpt"], "pixel-to-unrotated"
    )
    authority["_unrotated_to_pixel_matrix"] = _validate_rational_matrix(
        public["unrotated_mpt_to_pixel"], "unrotated-to-pixel"
    )
    return authority


def _validate_line_box(value: Any, *, width: int, height: int, label: str) -> list[Any]:
    if not isinstance(value, list) or len(value) != 4:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is not a four-coordinate box")
    coordinates = [_finite_number(item, label) for item in value]
    if not (
        0 <= coordinates[0] < coordinates[2] <= width
        and 0 <= coordinates[1] < coordinates[3] <= height
    ):
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is outside the rendered page")
    return coordinates


def _validate_line_polygon(value: Any, *, width: int, height: int, label: str) -> list[list[Any]]:
    if not isinstance(value, list) or len(value) != 4:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is not a quadrilateral")
    polygon = []
    for point in value:
        if not isinstance(point, list) or len(point) != 2:
            raise WaveOneRoleBLineOnlySupplementError(f"{label} point is malformed")
        x = _finite_number(point[0], label)
        y = _finite_number(point[1], label)
        if not 0 <= x <= width or not 0 <= y <= height:
            raise WaveOneRoleBLineOnlySupplementError(f"{label} point is outside the page")
        polygon.append([x, y])
    area_twice = abs(
        sum(
            polygon[index][0] * polygon[(index + 1) % 4][1]
            - polygon[(index + 1) % 4][0] * polygon[index][1]
            for index in range(4)
        )
    )
    if area_twice == 0:
        raise WaveOneRoleBLineOnlySupplementError(f"{label} is degenerate")
    return polygon


def _polygon_area_twice(polygon: Sequence[Sequence[int | float]]) -> int | float:
    return abs(
        sum(
            polygon[index][0] * polygon[(index + 1) % 4][1]
            - polygon[(index + 1) % 4][0] * polygon[index][1]
            for index in range(4)
        )
    )


def _canonical_geometry(
    pixel_box: list[Any],
    pixel_polygon: list[list[Any]],
    authority: dict[str, Any],
) -> tuple[list[int], list[list[int]]]:
    box_polygon = [
        [pixel_box[0], pixel_box[1]],
        [pixel_box[2], pixel_box[1]],
        [pixel_box[2], pixel_box[3]],
        [pixel_box[0], pixel_box[3]],
    ]
    try:
        canonical_box_polygon = transform_pixel_polygon_to_unrotated_mpt(box_polygon, authority)
        canonical_polygon = transform_pixel_polygon_to_unrotated_mpt(pixel_polygon, authority)
    except RuntimeError as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "authenticated line coordinate transform failed"
        ) from error
    canonical_box = [
        min(point[0] for point in canonical_box_polygon),
        min(point[1] for point in canonical_box_polygon),
        max(point[0] for point in canonical_box_polygon),
        max(point[1] for point in canonical_box_polygon),
    ]
    unrotated_width, unrotated_height = authority["unrotated_dimensions_mpt"]
    if (
        not isinstance(canonical_polygon, list)
        or len(canonical_polygon) != 4
        or any(
            not isinstance(point, list)
            or len(point) != 2
            or any(type(coordinate) is not int for coordinate in point)
            for point in canonical_polygon
        )
        or any(type(coordinate) is not int for coordinate in canonical_box)
        or not 0 <= canonical_box[0] < canonical_box[2] <= unrotated_width
        or not 0 <= canonical_box[1] < canonical_box[3] <= unrotated_height
        or any(
            not 0 <= point[0] <= unrotated_width or not 0 <= point[1] <= unrotated_height
            for point in canonical_polygon
        )
        or _polygon_area_twice(canonical_polygon) == 0
        or any(
            not canonical_box[0] <= point[0] <= canonical_box[2]
            or not canonical_box[1] <= point[1] <= canonical_box[3]
            for point in canonical_polygon
        )
    ):
        raise WaveOneRoleBLineOnlySupplementError(
            "canonical line geometry lies outside the unrotated page"
        )
    return canonical_box, canonical_polygon


def _safe_claims() -> dict[str, bool]:
    return {
        "page_read_complete_claimed": False,
        "ocr_complete_claimed": False,
        "word_geometry_accepted": False,
        "word_tokens_exposed": False,
        "blank_claimed": False,
        "absence_claimed": False,
        "statement_classification_attempted": False,
        "table_classification_attempted": False,
        "row_reconstruction_attempted": False,
        "cell_interpretation_attempted": False,
        "axis_interpretation_attempted": False,
        "schema_used": False,
        "mapping_used": False,
        "role_a_used": False,
        "historical_values_used": False,
        "bank_registry_metadata_used": False,
        "filename_metadata_used": False,
        "source_path_metadata_used": False,
        "new_ocr_inference_used": False,
        "network_used": False,
        "native_ocr_fallback_used": False,
    }


def _upstream_result_safety() -> dict[str, bool]:
    return {
        "statement_classified": False,
        "table_classified": False,
        "rows_reconstructed": False,
        "cells_interpreted": False,
        "absence_claimed": False,
        "bank_registry_metadata_used": False,
        "filename_metadata_used": False,
        "role_a_used": False,
        "schema_used": False,
        "mapping_used": False,
        "historical_values_used": False,
    }


def _validate_ppocrv6_schema_except_word_geometry(
    raw: dict[str, Any], *, pixel_width: int, pixel_height: int
) -> dict[str, int]:
    """Validate the whole provider schema after replacing only word geometry."""

    required_axes = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    if raw.get("return_word_box") is not True or any(
        not isinstance(raw.get(key), list) for key in required_axes
    ):
        raise WaveOneRoleBLineOnlySupplementError("raw PP axes are absent")
    counts = {key: len(raw[key]) for key in required_axes}
    if len(set(counts.values())) != 1:
        raise WaveOneRoleBLineOnlySupplementError("raw PP line axes are not aligned")
    sanitized = deepcopy(raw)
    for line_index in range(counts["rec_texts"]):
        line_box = raw["rec_boxes"][line_index]
        boxes = raw["text_word_boxes"][line_index]
        words = raw["text_word"][line_index]
        if (
            not isinstance(line_box, list)
            or len(line_box) != 4
            or not isinstance(boxes, list)
            or not isinstance(words, list)
            or len(boxes) != len(words)
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "raw PP quarantined subdivision axes are malformed"
            )
        replacements = []
        for box, word in zip(boxes, words, strict=True):
            if (
                not isinstance(word, str)
                or not isinstance(box, list)
                or len(box) != 4
                or any(
                    isinstance(value, bool)
                    or not isinstance(value, (int, float))
                    or not isfinite(value)
                    for value in box
                )
                or not box[0] < box[2]
                or not box[1] < box[3]
            ):
                raise WaveOneRoleBLineOnlySupplementError(
                    "raw PP quarantined subdivision schema drifted"
                )
            replacements.append(deepcopy(line_box))
        sanitized["text_word_boxes"][line_index] = replacements
    try:
        return validate_ppocrv6_payload(
            sanitized,
            pixel_width=pixel_width,
            pixel_height=pixel_height,
        )
    except RuntimeError as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "raw PP payload has a non-word-geometry structural failure"
        ) from error


def _validate_upstream_terminal_envelope(
    authority: FinalizedV2Authority,
    record: dict[str, Any],
    backend: dict[str, Any],
    result: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    if set(backend) != _UPSTREAM_BACKEND_KEYS or set(result) != _UPSTREAM_RESULT_KEYS:
        raise WaveOneRoleBLineOnlySupplementError("upstream terminal envelope fields drifted")
    if (
        backend.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_BACKEND_PAYLOAD_V3"
        or backend.get("claim_boundary")
        != "RAW_PINNED_PROVIDER_PAYLOAD_WITH_TERMINAL_BOUNDED_WORD_BOX_GEOMETRY_FAILURE"
        or result.get("format_version") != "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V3"
        or result.get("claim_boundary")
        != "SOURCE_VISIBLE_PAGE_RAW_OCR_EVIDENCE_WITH_UNRESOLVED_GEOMETRY"
        or backend.get("request_sha256") != record["request_sha256"]
        or result.get("request_sha256") != record["request_sha256"]
        or not _same_typed_json(backend.get("request"), record["request"])
        or not _same_typed_json(result.get("request"), record["request"])
        or backend.get("provider_identity_sha256")
        != record["request"].get("provider_identity_sha256")
        or result.get("provider_identity_sha256")
        != record["request"].get("provider_identity_sha256")
        or result.get("render_runtime_identity_sha256")
        != record["request"].get("render_runtime_identity_sha256")
        or result.get("source_sha256") != record["source_sha256"]
        or not _same_typed_json(result.get("source_size_bytes"), record["source_size_bytes"])
        or not _same_typed_json(result.get("physical_page"), record["physical_page"])
        or result.get("route") != _OCR_ROUTE
        or result.get("status") != _TERMINAL_STATUS
        or backend.get("word_box_normalization_ledger") is not None
        or not _same_typed_json(backend.get("render_ref"), record["render_ref"])
        or not _same_typed_json(result.get("input_render_ref"), record["render_ref"])
        or not _same_typed_json(result.get("backend_payload_ref"), record["backend_payload_ref"])
        or not _same_typed_json(
            backend.get("normalization_failure"), result.get("normalization_failure")
        )
        or result.get("lines") != []
        or result.get("words") != []
        or not _same_typed_json(result.get("metrics"), {"line_count": 0, "word_token_count": 0})
        or result.get("ocr_fallback_used") is not False
        or result.get("source_blank_claimed") is not False
        or not _same_typed_json(result.get("safety"), _upstream_result_safety())
    ):
        raise WaveOneRoleBLineOnlySupplementError("upstream terminal envelope identity drifted")
    raw = backend.get("raw_provider_payload")
    failure = backend.get("normalization_failure")
    coordinate_authority = result.get("coordinate_authority")
    if not isinstance(raw, dict) or not isinstance(failure, dict):
        raise WaveOneRoleBLineOnlySupplementError("upstream terminal payload is absent")
    if (
        set(failure)
        != {
            "format_version",
            "status",
            "reason",
            "policy_sha256",
            "control_identity_sha256",
            "normalization_producer_implementation_ledger_sha256",
            "pixel_dimensions",
            "raw_payload_sha256",
        }
        or failure.get("format_version") != "BANK_CORPUS_WAVE_1_PPOCRV6_NORMALIZATION_FAILURE_V1"
        or failure.get("status") != _TERMINAL_STATUS
        or failure.get("reason") != _FAILURE_REASON
        or failure.get("policy_sha256")
        != authority.control["word_box_normalization"]["policy_sha256"]
        or failure.get("control_identity_sha256") != authority.control["control_identity_sha256"]
        or failure.get("normalization_producer_implementation_ledger_sha256")
        != authority.control["word_box_normalization"][
            "normalization_producer_implementation_ledger_sha256"
        ]
        or failure.get("raw_payload_sha256") != _canonical_sha256(raw)
        or not _same_typed_json(
            failure.get("pixel_dimensions"),
            coordinate_authority.get("pixel_dimensions")
            if isinstance(coordinate_authority, dict)
            else None,
        )
    ):
        raise WaveOneRoleBLineOnlySupplementError("upstream normalization failure drifted")
    return raw, failure, _restore_coordinate_authority(coordinate_authority)


def _project_terminal_page(
    project_root: Path,
    authority: FinalizedV2Authority,
    supplement_control: dict[str, Any],
    record: dict[str, Any],
) -> dict[str, Any]:
    backend = _json_object(
        _read_upstream_object(project_root, record["backend_payload_ref"], ".json"),
        "upstream terminal backend",
    )
    result = _json_object(
        _read_upstream_object(project_root, record["result_ref"], ".json"),
        "upstream terminal result",
    )
    raw, failure, coordinate_authority = _validate_upstream_terminal_envelope(
        authority, record, backend, result
    )
    required_axes = (
        "rec_texts",
        "rec_scores",
        "rec_polys",
        "rec_boxes",
        "text_word_boxes",
        "text_word",
    )
    if raw.get("return_word_box") is not True or any(
        not isinstance(raw.get(key), list) for key in required_axes
    ):
        raise WaveOneRoleBLineOnlySupplementError("raw PP axes are absent")
    counts = {key: len(raw[key]) for key in required_axes}
    if len(set(counts.values())) != 1:
        raise WaveOneRoleBLineOnlySupplementError("raw PP line axes are not aligned")
    width, height = coordinate_authority["pixel_dimensions"]
    validated_counts = _validate_ppocrv6_schema_except_word_geometry(
        raw, pixel_width=width, pixel_height=height
    )
    if validated_counts["line_count"] != counts["rec_texts"]:
        raise WaveOneRoleBLineOnlySupplementError("raw PP validated line accounting drifted")
    lines = []
    hidden_word_axes = []
    subdivisions_by_line = []
    excluded_empty_line_axis_count = 0
    for index in range(counts["rec_texts"]):
        text = raw["rec_texts"][index]
        score = raw["rec_scores"][index]
        if not isinstance(text, str):
            raise WaveOneRoleBLineOnlySupplementError("raw PP line text is not a string")
        score = _finite_number(score, "raw PP line score")
        if not 0 <= score <= 1:
            raise WaveOneRoleBLineOnlySupplementError("raw PP line score is outside [0,1]")
        pixel_box = _validate_line_box(
            raw["rec_boxes"][index],
            width=width,
            height=height,
            label="raw PP line box",
        )
        pixel_polygon = _validate_line_polygon(
            raw["rec_polys"][index],
            width=width,
            height=height,
            label="raw PP line polygon",
        )
        subdivision_boxes = raw["text_word_boxes"][index]
        subdivision_text = raw["text_word"][index]
        if (
            not isinstance(subdivision_boxes, list)
            or not isinstance(subdivision_text, list)
            or len(subdivision_boxes) != len(subdivision_text)
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "raw PP quarantined subdivision axes are not aligned"
            )
        for box, word in zip(subdivision_boxes, subdivision_text, strict=True):
            if not isinstance(word, str) or not isinstance(box, list) or len(box) != 4:
                raise WaveOneRoleBLineOnlySupplementError(
                    "raw PP quarantined subdivision schema drifted"
                )
            coordinates = [
                _finite_number(value, "raw PP quarantined subdivision box") for value in box
            ]
            if not coordinates[0] < coordinates[2] or not coordinates[1] < coordinates[3]:
                raise WaveOneRoleBLineOnlySupplementError(
                    "raw PP quarantined subdivision box is not positive"
                )
        hidden_word_axes.append([deepcopy(subdivision_text), deepcopy(subdivision_boxes)])
        subdivisions_by_line.append(len(subdivision_text))
        canonical_box, canonical_polygon = _canonical_geometry(
            pixel_box, pixel_polygon, coordinate_authority
        )
        if text == "":
            excluded_empty_line_axis_count += 1
        else:
            lines.append(
                {
                    "format_version": _LINE_FORMAT,
                    "line_index": index,
                    "text": text,
                    "score": score,
                    "pixel_rec_box": deepcopy(pixel_box),
                    "pixel_rec_polygon": deepcopy(pixel_polygon),
                    "canonical_rec_box_mpt": canonical_box,
                    "canonical_rec_polygon_mpt": canonical_polygon,
                }
            )
    try:
        normalize_ppocrv6_word_boxes(
            raw,
            pixel_width=width,
            pixel_height=height,
            authority=authority.control["word_box_normalization"],
        )
    except WaveOneRoleBWordBoxNormalizationError:
        pass
    else:
        raise WaveOneRoleBLineOnlySupplementError(
            "upstream terminal payload is unexpectedly word-box normalizable"
        )
    disposition = _ACCEPTED_DISPOSITION if lines else _REJECTED_DISPOSITION
    accepted_lines = lines if disposition == _ACCEPTED_DISPOSITION else []
    quarantine = {
        "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_WORD_SUBDIVISION_QUARANTINE_V1",
        "status": "QUARANTINED_UNRESOLVED_WORD_BOX_GEOMETRY",
        "reason": _FAILURE_REASON,
        "ordered_subdivision_counts_by_line": subdivisions_by_line,
        "total_subdivision_count": sum(subdivisions_by_line),
        "word_axes_sha256": _canonical_sha256(hidden_word_axes),
        "raw_provider_payload_sha256": _canonical_sha256(raw),
        "raw_backend_payload_ref": deepcopy(record["backend_payload_ref"]),
        "word_text_exposed": False,
        "word_geometry_exposed": False,
        "accepted_word_count": 0,
    }
    evidence = {
        "format_version": _PAGE_FORMAT,
        "supplemental_disposition": disposition,
        "claim_boundary": _CLAIM_BOUNDARY,
        "control_identity_sha256": supplement_control["control_identity_sha256"],
        "upstream": {
            "aggregate_identity_sha256": authority.aggregate["aggregate_identity_sha256"],
            "status": _TERMINAL_STATUS,
            "status_preserved": True,
            "normalization_failure_reason": _FAILURE_REASON,
            "request_sha256": record["request_sha256"],
            "request_ordinal": record["request_ordinal"],
            "document_id": record["document_id"],
            "physical_page": record["physical_page"],
            "source_sha256": record["source_sha256"],
            "backend_payload_ref": deepcopy(record["backend_payload_ref"]),
            "result_ref": deepcopy(record["result_ref"]),
            "normalization_failure": deepcopy(failure),
        },
        "coordinate_authority": {
            key: deepcopy(value)
            for key, value in coordinate_authority.items()
            if not key.startswith("_")
        },
        "lines": accepted_lines,
        "words": [],
        "quarantine": quarantine,
        "metrics": {
            "validated_line_axis_count": counts["rec_texts"],
            "excluded_empty_line_axis_count": excluded_empty_line_axis_count,
            "accepted_line_count": len(accepted_lines),
            "accepted_word_count": 0,
            "quarantined_subdivision_count": quarantine["total_subdivision_count"],
        },
        "safety": _safe_claims(),
    }
    return evidence


def _terminal_request_descriptor(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_ordinal": record["request_ordinal"],
        "request_sha256": record["request_sha256"],
        "document_id": record["document_id"],
        "physical_page": record["physical_page"],
        "source_sha256": record["source_sha256"],
        "backend_payload_ref": deepcopy(record["backend_payload_ref"]),
        "result_ref": deepcopy(record["result_ref"]),
        "upstream_status": record["status"],
        "upstream_unresolved": record["unresolved"],
    }


def _build_control_from_authority(
    policy: dict[str, Any],
    executor: dict[str, Any],
    authority: FinalizedV2Authority,
) -> dict[str, Any]:
    records = _terminal_records(authority.aggregate)
    aggregate_ref = {
        "path": "full-reader-aggregate.json",
        "sha256": sha256_bytes(authority.aggregate_payload),
        "size_bytes": len(authority.aggregate_payload),
    }
    control_ref = {
        "path": "full-reader-execution-control.json",
        "sha256": sha256_bytes(authority.control_payload),
        "size_bytes": len(authority.control_payload),
    }
    control = {
        "format_version": _CONTROL_FORMAT,
        "status": "READY_FOR_AUTHENTICATED_POST_V2_LINE_ONLY_SUPPLEMENT",
        "claim_boundary": _CLAIM_BOUNDARY,
        "policy": {
            "path": POLICY_RELATIVE_PATH.as_posix(),
            "sha256": POLICY_SHA256,
            "size_bytes": POLICY_SIZE_BYTES,
        },
        "upstream": {
            "aggregate": aggregate_ref,
            "aggregate_identity_sha256": authority.aggregate["aggregate_identity_sha256"],
            "aggregate_status": authority.aggregate["status"],
            "control": control_ref,
            "control_identity_sha256": authority.control["control_identity_sha256"],
            "sealed_plan": deepcopy(authority.aggregate["sealed_plan"]),
            "executor_git": deepcopy(authority.aggregate["executor_git"]),
            "executor_implementation_ledger_sha256": authority.aggregate[
                "executor_implementation_ledger"
            ]["sha256"],
            "word_box_normalization": deepcopy(authority.control["word_box_normalization"]),
            "verified_request_count": authority.aggregate["accounting"]["request_count"],
        },
        "executor_git": deepcopy(executor["git"]),
        "executor_implementation_ledger": deepcopy(executor["implementation_ledger"]),
        "terminal_requests": [_terminal_request_descriptor(record) for record in records],
        "execution_contract": {
            "output_root": OUTPUT_RELATIVE_ROOT.as_posix(),
            "object_store": "objects/sha256",
            "checkpoint_directory": "checkpoints",
            "checkpoint": "ONE_IMMUTABLE_REQUEST_CHECKPOINT_WITH_ORDERED_HASH_CHAIN",
            "resume": "EXACT_REPLAY_WITH_ZERO_NEW_PROJECTIONS",
            "no_ocr": True,
            "no_network": True,
            "no_external_provider": True,
            "timings_in_identity": False,
        },
        "accounting": {
            "upstream_request_count": 1_449,
            "terminal_denominator_count": len(records),
            "required_supplemental_disposition_count": len(records),
            "expected_missing_terminal_count": 0,
            "expected_duplicate_terminal_count": 0,
            "expected_foreign_terminal_count": 0,
        },
        "safety": _safe_claims(),
    }
    control["control_identity_sha256"] = _canonical_sha256(control)
    return control


def build_authenticated_line_only_control(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Build the control only after the finalized V2 graph passes full replay."""

    project_root = project_root.resolve()
    authority = _authenticate_finalized_v2(project_root, model_cache=model_cache.resolve())
    policy = _load_policy(project_root)
    executor = _executor_identity(project_root, require_clean=True)
    control = _build_control_from_authority(policy, executor, authority)
    _recheck_upstream_authority(project_root, authority)
    return control


def _publish_exclusive(project_root: Path, directory: Path, filename: str, payload: bytes) -> Path:
    try:
        return sentinel._publish_exclusive(  # noqa: SLF001 - authenticated publication substrate
            project_root, directory, filename, payload
        )
    except sentinel.WaveOneRoleBSentinelError as error:
        raise WaveOneRoleBLineOnlySupplementError(str(error)) from error


def _recover_root_publication_pairs(project_root: Path) -> None:
    """Recover only a complete, exact control/aggregate hardlink publication pair.

    This mutating recovery is called only while the supplement execution lease is
    held.  The public read-only verifier never calls it.
    """

    expected_plain = {
        LEASE_FILENAME,
        CONTROL_FILENAME,
        AGGREGATE_FILENAME,
        "objects",
        "checkpoints",
    }
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT, create=True
        ) as (_directory, directory_fd):
            names = sorted(os.listdir(directory_fd))
            temporaries: dict[str, tuple[str, os.stat_result]] = {}
            finals: dict[str, os.stat_result] = {}
            for name in names:
                match = _ROOT_PUBLICATION_TEMP.fullmatch(name)
                if match is not None:
                    final_name = match.group("final")
                    if final_name in temporaries:
                        raise WaveOneRoleBLineOnlySupplementError(
                            "multiple root publication temporaries exist"
                        )
                    temporary = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                    temporaries[final_name] = (name, temporary)
                    continue
                if name not in expected_plain:
                    raise WaveOneRoleBLineOnlySupplementError("foreign line-only root entry exists")
                observed = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)
                if name in {"objects", "checkpoints"}:
                    if not stat.S_ISDIR(observed.st_mode):
                        raise WaveOneRoleBLineOnlySupplementError(
                            "line-only root directory entry drifted"
                        )
                elif name == LEASE_FILENAME:
                    if (
                        not stat.S_ISREG(observed.st_mode)
                        or stat.S_IMODE(observed.st_mode) != 0o600
                        or observed.st_nlink != 1
                        or observed.st_size != 0
                    ):
                        raise WaveOneRoleBLineOnlySupplementError(
                            "line-only root lease entry drifted"
                        )
                else:
                    finals[name] = observed

            recoverable: list[tuple[str, str, tuple[int, int, int, int, int], bytes]] = []
            for final_name in (CONTROL_FILENAME, AGGREGATE_FILENAME):
                final = finals.get(final_name)
                temporary_entry = temporaries.get(final_name)
                if final is None and temporary_entry is not None:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication temporary has no final link"
                    )
                if final is None:
                    continue
                if not stat.S_ISREG(final.st_mode) or stat.S_IMODE(final.st_mode) != 0o444:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication final is not immutable"
                    )
                if final.st_nlink == 1:
                    if temporary_entry is not None:
                        raise WaveOneRoleBLineOnlySupplementError(
                            "standalone root publication temporary exists"
                        )
                    continue
                if final.st_nlink != 2 or temporary_entry is None:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication link topology is unexplained"
                    )
                temporary_name, temporary = temporary_entry
                identity = (
                    final.st_dev,
                    final.st_ino,
                    final.st_size,
                    final.st_mtime_ns,
                    final.st_ctime_ns,
                )
                if (
                    not stat.S_ISREG(temporary.st_mode)
                    or stat.S_IMODE(temporary.st_mode) != 0o444
                    or temporary.st_nlink != 2
                    or (
                        temporary.st_dev,
                        temporary.st_ino,
                        temporary.st_size,
                        temporary.st_mtime_ns,
                        temporary.st_ctime_ns,
                    )
                    != identity
                ):
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication pair identity drifted"
                    )
                final_payload, opened_final = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, final_name
                )
                temp_payload, opened_temp = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, temporary_name
                )
                if (
                    final_payload != temp_payload
                    or (
                        opened_final.st_dev,
                        opened_final.st_ino,
                        opened_final.st_size,
                        opened_final.st_mtime_ns,
                        opened_final.st_ctime_ns,
                    )
                    != identity
                    or (
                        opened_temp.st_dev,
                        opened_temp.st_ino,
                        opened_temp.st_size,
                        opened_temp.st_mtime_ns,
                        opened_temp.st_ctime_ns,
                    )
                    != identity
                ):
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication pair content drifted"
                    )
                recoverable.append((final_name, temporary_name, identity, final_payload))

            for final_name, temporary_name, identity, expected_payload in recoverable:
                before_unlink = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
                if (
                    before_unlink.st_dev,
                    before_unlink.st_ino,
                    before_unlink.st_size,
                    before_unlink.st_mtime_ns,
                    before_unlink.st_ctime_ns,
                ) != identity:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication temporary changed before recovery"
                    )
                os.unlink(temporary_name, dir_fd=directory_fd)
                os.fsync(directory_fd)
                payload, final = sentinel._hash_open_at(  # noqa: SLF001
                    directory_fd, final_name
                )
                if (
                    payload != expected_payload
                    or not stat.S_ISREG(final.st_mode)
                    or stat.S_IMODE(final.st_mode) != 0o444
                    or final.st_nlink != 1
                    or (final.st_dev, final.st_ino, final.st_size) != identity[:3]
                ):
                    raise WaveOneRoleBLineOnlySupplementError(
                        "root publication recovery final drifted"
                    )
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only root publication recovery failed"
        ) from error


def publish_authenticated_line_only_control(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    policy = _load_policy(project_root)
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    authority = _authenticate_finalized_v2(project_root, model_cache=model_cache.resolve())
    executor = _executor_identity(project_root, require_clean=True)
    control = _build_control_from_authority(policy, executor, authority)
    _recheck_upstream_authority(project_root, authority)
    with _execution_lease(project_root):
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        _recover_root_publication_pairs(project_root)
        _recheck_upstream_authority(project_root, authority)
        if not _same_typed_json(_executor_identity(project_root, require_clean=True), executor):
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only executor changed before control publication"
            )
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        _publish_exclusive(
            project_root, OUTPUT_RELATIVE_ROOT, CONTROL_FILENAME, _canonical_bytes(control)
        )
        replay = _replay_published_control(project_root, policy, authority)
        _recheck_upstream_authority(project_root, authority)
    return replay


def _object_reference(payload: bytes) -> dict[str, Any]:
    digest = sha256_bytes(payload)
    return {
        "path": f"objects/sha256/{digest[:2]}/{digest}.json",
        "sha256": digest,
        "size_bytes": len(payload),
    }


def _put_object(project_root: Path, payload: bytes) -> dict[str, Any]:
    reference = _object_reference(payload)
    digest = reference["sha256"]
    _publish_exclusive(
        project_root,
        OUTPUT_RELATIVE_ROOT / "objects" / "sha256" / digest[:2],
        f"{digest}.json",
        payload,
    )
    return reference


def _read_output_object(project_root: Path, reference: Mapping[str, Any]) -> bytes:
    if not isinstance(reference, Mapping) or set(reference) != {
        "path",
        "sha256",
        "size_bytes",
    }:
        raise WaveOneRoleBLineOnlySupplementError("line-only object reference fields drifted")
    digest = reference.get("sha256")
    size = reference.get("size_bytes")
    expected_path = f"objects/sha256/{str(digest)[:2]}/{digest}.json"
    if (
        not _is_sha256(digest)
        or type(size) is not int
        or size < 0
        or reference.get("path") != expected_path
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only object reference drifted")
    payload, _identity = _read_immutable_relative(
        project_root,
        OUTPUT_RELATIVE_ROOT / expected_path,
        label="line-only content-addressed object",
    )
    if len(payload) != size or sha256_bytes(payload) != digest:
        raise WaveOneRoleBLineOnlySupplementError("line-only object content drifted")
    return payload


def _read_published_control(project_root: Path) -> dict[str, Any]:
    payload, _identity = _read_immutable_relative(
        project_root,
        OUTPUT_RELATIVE_ROOT / CONTROL_FILENAME,
        label="published line-only control",
    )
    control = _json_object(payload, "published line-only control")
    identity = control.get("control_identity_sha256")
    if (
        control.get("format_version") != _CONTROL_FORMAT
        or not _is_sha256(identity)
        or _canonical_sha256(
            {key: value for key, value in control.items() if key != "control_identity_sha256"}
        )
        != identity
    ):
        raise WaveOneRoleBLineOnlySupplementError("published line-only control drifted")
    return control


def _replay_published_control(
    project_root: Path,
    policy: dict[str, Any],
    authority: FinalizedV2Authority,
) -> dict[str, Any]:
    published = _read_published_control(project_root)
    _validate_published_executor(project_root, published)
    executor = {
        "git": deepcopy(published["executor_git"]),
        "implementation_ledger": deepcopy(published["executor_implementation_ledger"]),
    }
    expected = _build_control_from_authority(policy, executor, authority)
    if not _same_typed_json(expected, published):
        raise WaveOneRoleBLineOnlySupplementError(
            "published line-only control structural replay drifted"
        )
    return published


def _load_or_publish_control(
    project_root: Path,
    policy: dict[str, Any],
    authority: FinalizedV2Authority,
) -> dict[str, Any]:
    try:
        return _replay_published_control(project_root, policy, authority)
    except WaveOneRoleBLineOnlySupplementError:
        if not _relative_entry_is_absent(project_root, OUTPUT_RELATIVE_ROOT / CONTROL_FILENAME):
            raise
    executor = _executor_identity(project_root, require_clean=True)
    control = _build_control_from_authority(policy, executor, authority)
    _publish_exclusive(
        project_root, OUTPUT_RELATIVE_ROOT, CONTROL_FILENAME, _canonical_bytes(control)
    )
    return _replay_published_control(project_root, policy, authority)


def _relative_entry_is_absent(project_root: Path, relative: Path) -> bool:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, relative.parent, create=False
        ) as (_directory, directory_fd):
            try:
                os.stat(relative.name, dir_fd=directory_fd, follow_symlinks=False)
            except FileNotFoundError:
                return True
            return False
    except FileNotFoundError:
        return True
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only publication existence check failed"
        ) from error


def _ensure_capacity(project_root: Path, minimum_free_space_bytes: int) -> None:
    if type(minimum_free_space_bytes) is not int or minimum_free_space_bytes <= 0:
        raise WaveOneRoleBLineOnlySupplementError("minimum free-space policy drifted")
    if shutil.disk_usage(project_root).free < minimum_free_space_bytes:
        raise WaveOneRoleBLineOnlySupplementError("insufficient space for line-only supplement")


def _validate_lock_identity(directory_fd: int, descriptor: int, expected: tuple[int, int]) -> None:
    opened = os.fstat(descriptor)
    named = os.stat(LEASE_FILENAME, dir_fd=directory_fd, follow_symlinks=False)
    if (
        not stat.S_ISREG(opened.st_mode)
        or stat.S_IMODE(opened.st_mode) != 0o600
        or opened.st_nlink != 1
        or opened.st_size != 0
        or (opened.st_dev, opened.st_ino) != expected
        or (named.st_dev, named.st_ino) != expected
        or stat.S_IMODE(named.st_mode) != 0o600
        or named.st_nlink != 1
        or named.st_size != 0
    ):
        raise WaveOneRoleBLineOnlySupplementError("line-only execution lease drifted")


@contextmanager
def _execution_lease(project_root: Path) -> Iterator[None]:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT, create=True
        ) as (_directory, directory_fd):
            descriptor = os.open(
                LEASE_FILENAME,
                os.O_RDWR | os.O_CREAT | getattr(os, "O_CLOEXEC", 0) | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=directory_fd,
            )
            try:
                opened = os.fstat(descriptor)
                expected = (opened.st_dev, opened.st_ino)
                _validate_lock_identity(directory_fd, descriptor, expected)
                fcntl.flock(descriptor, fcntl.LOCK_EX)
                _validate_lock_identity(directory_fd, descriptor, expected)
                yield
                _validate_lock_identity(directory_fd, descriptor, expected)
            finally:
                try:
                    fcntl.flock(descriptor, fcntl.LOCK_UN)
                finally:
                    os.close(descriptor)
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only execution lease could not be held safely"
        ) from error


def _checkpoint_filename(generation: int, request_sha256: str) -> str:
    if type(generation) is not int or generation <= 0 or not _is_sha256(request_sha256):
        raise WaveOneRoleBLineOnlySupplementError("checkpoint filename identity drifted")
    return f"{generation:04d}-{request_sha256}.json"


def _checkpoint_payload(
    control: dict[str, Any],
    record: dict[str, Any],
    evidence: dict[str, Any],
    evidence_ref: dict[str, Any],
    *,
    generation: int,
    previous_checkpoint_sha256: str | None,
) -> dict[str, Any]:
    if previous_checkpoint_sha256 is not None and not _is_sha256(previous_checkpoint_sha256):
        raise WaveOneRoleBLineOnlySupplementError("checkpoint predecessor drifted")
    return {
        "format_version": _CHECKPOINT_FORMAT,
        "status": "TERMINAL_PAGE_SUPPLEMENTAL_DISPOSITION_CHECKPOINTED",
        "claim_boundary": _CLAIM_BOUNDARY,
        "control_identity_sha256": control["control_identity_sha256"],
        "generation": generation,
        "previous_checkpoint_sha256": previous_checkpoint_sha256,
        "request_ordinal": record["request_ordinal"],
        "request_sha256": record["request_sha256"],
        "document_id": record["document_id"],
        "physical_page": record["physical_page"],
        "upstream_status": _TERMINAL_STATUS,
        "supplemental_disposition": evidence["supplemental_disposition"],
        "evidence_ref": deepcopy(evidence_ref),
    }


def _checkpoint_entries(
    project_root: Path, *, create: bool, recover: bool
) -> list[tuple[str, bytes, os.stat_result]]:
    try:
        with sentinel._held_directory(  # noqa: SLF001
            project_root, OUTPUT_RELATIVE_ROOT / "checkpoints", create=create
        ) as (_directory, directory_fd):
            if recover:
                _recover_checkpoint_publication_pairs(directory_fd)
            entries = []
            for name in sorted(os.listdir(directory_fd)):
                if _CHECKPOINT_NAME.fullmatch(name) is None:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "foreign line-only checkpoint entry exists"
                    )
                payload, identity = sentinel._hash_open_at(directory_fd, name)  # noqa: SLF001
                if stat.S_IMODE(identity.st_mode) != 0o444 or identity.st_nlink != 1:
                    raise WaveOneRoleBLineOnlySupplementError(
                        "line-only checkpoint is not immutable"
                    )
                entries.append((name, payload, identity))
            return entries
    except FileNotFoundError:
        if create:
            raise
        return []
    except (OSError, sentinel.WaveOneRoleBSentinelError) as error:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only checkpoint directory could not be read safely"
        ) from error


def _recover_checkpoint_publication_pairs(directory_fd: int) -> None:
    """Recover only exact completed checkpoint hardlink publication windows."""

    names = sorted(os.listdir(directory_fd))
    finals: dict[str, os.stat_result] = {}
    temporaries: dict[str, tuple[str, os.stat_result]] = {}
    for name in names:
        match = _CHECKPOINT_TEMP.fullmatch(name)
        if match is not None:
            final_name = match.group("final")
            if final_name in temporaries:
                raise WaveOneRoleBLineOnlySupplementError(
                    "multiple checkpoint publication temporaries exist"
                )
            temporaries[final_name] = (
                name,
                os.stat(name, dir_fd=directory_fd, follow_symlinks=False),
            )
            continue
        if _CHECKPOINT_NAME.fullmatch(name) is None:
            raise WaveOneRoleBLineOnlySupplementError("foreign line-only checkpoint entry exists")
        finals[name] = os.stat(name, dir_fd=directory_fd, follow_symlinks=False)

    recoverable: list[tuple[str, str, tuple[int, int, int, int, int], bytes]] = []
    for final_name, (temporary_name, temporary) in temporaries.items():
        final = finals.get(final_name)
        if final is None:
            raise WaveOneRoleBLineOnlySupplementError(
                "checkpoint publication temporary has no final link"
            )
        identity = (
            final.st_dev,
            final.st_ino,
            final.st_size,
            final.st_mtime_ns,
            final.st_ctime_ns,
        )
        if (
            not stat.S_ISREG(final.st_mode)
            or not stat.S_ISREG(temporary.st_mode)
            or stat.S_IMODE(final.st_mode) != 0o444
            or stat.S_IMODE(temporary.st_mode) != 0o444
            or final.st_nlink != 2
            or temporary.st_nlink != 2
            or (
                temporary.st_dev,
                temporary.st_ino,
                temporary.st_size,
                temporary.st_mtime_ns,
                temporary.st_ctime_ns,
            )
            != identity
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "checkpoint publication pair identity drifted"
            )
        final_payload, opened_final = sentinel._hash_open_at(  # noqa: SLF001
            directory_fd, final_name
        )
        temp_payload, opened_temp = sentinel._hash_open_at(  # noqa: SLF001
            directory_fd, temporary_name
        )
        if (
            final_payload != temp_payload
            or (
                opened_final.st_dev,
                opened_final.st_ino,
                opened_final.st_size,
                opened_final.st_mtime_ns,
                opened_final.st_ctime_ns,
            )
            != identity
            or (
                opened_temp.st_dev,
                opened_temp.st_ino,
                opened_temp.st_size,
                opened_temp.st_mtime_ns,
                opened_temp.st_ctime_ns,
            )
            != identity
        ):
            raise WaveOneRoleBLineOnlySupplementError("checkpoint publication pair content drifted")
        recoverable.append((final_name, temporary_name, identity, final_payload))
    for final_name, final in finals.items():
        if (
            not stat.S_ISREG(final.st_mode)
            or stat.S_IMODE(final.st_mode) != 0o444
            or final.st_nlink not in {1, 2}
            or (final.st_nlink == 2) != (final_name in temporaries)
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "checkpoint publication final topology drifted"
            )

    for final_name, temporary_name, identity, expected_payload in recoverable:
        before_unlink = os.stat(temporary_name, dir_fd=directory_fd, follow_symlinks=False)
        if (
            before_unlink.st_dev,
            before_unlink.st_ino,
            before_unlink.st_size,
            before_unlink.st_mtime_ns,
            before_unlink.st_ctime_ns,
        ) != identity:
            raise WaveOneRoleBLineOnlySupplementError(
                "checkpoint temporary changed before recovery"
            )
        os.unlink(temporary_name, dir_fd=directory_fd)
        os.fsync(directory_fd)
        payload, final = sentinel._hash_open_at(directory_fd, final_name)  # noqa: SLF001
        if (
            payload != expected_payload
            or stat.S_IMODE(final.st_mode) != 0o444
            or final.st_nlink != 1
            or (final.st_dev, final.st_ino, final.st_size) != identity[:3]
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "checkpoint publication recovery final drifted"
            )


def _load_checkpoints(
    project_root: Path,
    control: dict[str, Any],
    terminal_records: list[dict[str, Any]],
    *,
    create: bool,
    recover: bool,
) -> tuple[list[dict[str, Any]], str | None]:
    entries = _checkpoint_entries(project_root, create=create, recover=recover)
    if len(entries) > len(terminal_records):
        raise WaveOneRoleBLineOnlySupplementError("too many line-only checkpoints exist")
    checkpoints = []
    previous = None
    for generation, (name, payload, _identity) in enumerate(entries, start=1):
        record = terminal_records[generation - 1]
        if name != _checkpoint_filename(generation, record["request_sha256"]):
            raise WaveOneRoleBLineOnlySupplementError("line-only checkpoint chain order drifted")
        checkpoint = _json_object(payload, "line-only checkpoint")
        expected_fields = {
            "format_version",
            "status",
            "claim_boundary",
            "control_identity_sha256",
            "generation",
            "previous_checkpoint_sha256",
            "request_ordinal",
            "request_sha256",
            "document_id",
            "physical_page",
            "upstream_status",
            "supplemental_disposition",
            "evidence_ref",
        }
        if (
            set(checkpoint) != expected_fields
            or checkpoint.get("format_version") != _CHECKPOINT_FORMAT
            or checkpoint.get("status") != "TERMINAL_PAGE_SUPPLEMENTAL_DISPOSITION_CHECKPOINTED"
            or checkpoint.get("claim_boundary") != _CLAIM_BOUNDARY
            or checkpoint.get("control_identity_sha256") != control["control_identity_sha256"]
            or type(checkpoint.get("generation")) is not int
            or checkpoint.get("generation") != generation
            or checkpoint.get("previous_checkpoint_sha256") != previous
            or type(checkpoint.get("request_ordinal")) is not int
            or checkpoint.get("request_ordinal") != record["request_ordinal"]
            or checkpoint.get("request_sha256") != record["request_sha256"]
            or checkpoint.get("document_id") != record["document_id"]
            or type(checkpoint.get("physical_page")) is not int
            or checkpoint.get("physical_page") != record["physical_page"]
            or checkpoint.get("upstream_status") != _TERMINAL_STATUS
            or checkpoint.get("supplemental_disposition")
            not in {_ACCEPTED_DISPOSITION, _REJECTED_DISPOSITION}
        ):
            raise WaveOneRoleBLineOnlySupplementError("line-only checkpoint drifted")
        previous = sha256_bytes(payload)
        checkpoints.append(checkpoint)
    return checkpoints, previous


def _validate_checkpoint_evidence(
    project_root: Path,
    authority: FinalizedV2Authority,
    control: dict[str, Any],
    record: dict[str, Any],
    checkpoint: dict[str, Any],
) -> dict[str, Any]:
    expected = _project_terminal_page(project_root, authority, control, record)
    payload = _read_output_object(project_root, checkpoint["evidence_ref"])
    observed = _json_object(payload, "line-only page evidence")
    if (
        not _same_typed_json(observed, expected)
        or checkpoint["supplemental_disposition"] != expected["supplemental_disposition"]
    ):
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only page evidence deterministic replay drifted"
        )
    return observed


def run_authenticated_line_only_supplement(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Project every finalized V2 word-geometry terminal page without inference."""

    project_root = project_root.resolve()
    authority = _authenticate_finalized_v2(project_root, model_cache=model_cache.resolve())
    policy = _load_policy(project_root)
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    records = _terminal_records(authority.aggregate)
    new_count = 0
    with _execution_lease(project_root):
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        _recover_root_publication_pairs(project_root)
        control = _load_or_publish_control(project_root, policy, authority)
        _recheck_upstream_authority(project_root, authority)
        checkpoints, previous = _load_checkpoints(
            project_root, control, records, create=True, recover=True
        )
        for index, checkpoint in enumerate(checkpoints):
            _validate_checkpoint_evidence(
                project_root, authority, control, records[index], checkpoint
            )
        for index in range(len(checkpoints), len(records)):
            _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
            record = records[index]
            evidence = _project_terminal_page(project_root, authority, control, record)
            _recheck_upstream_authority(project_root, authority)
            evidence_ref = _put_object(project_root, _canonical_bytes(evidence))
            _recheck_upstream_authority(project_root, authority)
            checkpoint = _checkpoint_payload(
                control,
                record,
                evidence,
                evidence_ref,
                generation=index + 1,
                previous_checkpoint_sha256=previous,
            )
            payload = _canonical_bytes(checkpoint)
            _publish_exclusive(
                project_root,
                OUTPUT_RELATIVE_ROOT / "checkpoints",
                _checkpoint_filename(index + 1, record["request_sha256"]),
                payload,
            )
            previous = sha256_bytes(payload)
            checkpoints.append(checkpoint)
            new_count += 1
        if len(checkpoints) != len(records):
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only run did not disposition the terminal denominator"
            )
        verified_aggregate = _verify_with_authority(project_root, policy, authority)
        if verified_aggregate["control"]["identity_sha256"] != control["control_identity_sha256"]:
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only run verification control identity drifted"
            )
    _recheck_upstream_authority(project_root, authority)
    return {
        "status": (
            "COMPLETE_LINE_ONLY_RUN_WITH_ZERO_REQUIRED_PROJECTIONS"
            if not records
            else (
                "COMPLETE_LINE_ONLY_RESUME_WITH_ZERO_NEW_PROJECTIONS"
                if new_count == 0
                else "COMPLETE_AUTHENTICATED_LINE_ONLY_PAGE_CHECKPOINTS"
            )
        ),
        "control_identity_sha256": control["control_identity_sha256"],
        "terminal_denominator_count": len(records),
        "checkpoint_count": len(checkpoints),
        "new_projection_count": new_count,
        "ocr_inference_count": 0,
        "network_call_count": 0,
    }


def _build_aggregate(
    authority: FinalizedV2Authority,
    control: dict[str, Any],
    terminal_records: list[dict[str, Any]],
    checkpoints: list[dict[str, Any]],
    evidence_records: list[dict[str, Any]],
) -> dict[str, Any]:
    if not (len(terminal_records) == len(checkpoints) == len(evidence_records)):
        raise WaveOneRoleBLineOnlySupplementError("line-only aggregate denominator is incomplete")
    page_records = []
    dispositions = Counter()
    accepted_line_count = 0
    validated_line_axis_count = 0
    excluded_empty_line_axis_count = 0
    quarantined_subdivision_count = 0
    quarantine_hashes = []
    for upstream, checkpoint, evidence in zip(
        terminal_records, checkpoints, evidence_records, strict=True
    ):
        disposition = evidence["supplemental_disposition"]
        dispositions[disposition] += 1
        metrics = evidence["metrics"]
        if (
            metrics["validated_line_axis_count"]
            != metrics["accepted_line_count"] + metrics["excluded_empty_line_axis_count"]
        ):
            raise WaveOneRoleBLineOnlySupplementError(
                "line-only page line accounting does not reconcile"
            )
        accepted_line_count += metrics["accepted_line_count"]
        validated_line_axis_count += metrics["validated_line_axis_count"]
        excluded_empty_line_axis_count += metrics["excluded_empty_line_axis_count"]
        quarantined_subdivision_count += metrics["quarantined_subdivision_count"]
        quarantine_hashes.append(evidence["quarantine"]["word_axes_sha256"])
        page_records.append(
            {
                "request_ordinal": upstream["request_ordinal"],
                "request_sha256": upstream["request_sha256"],
                "document_id": upstream["document_id"],
                "physical_page": upstream["physical_page"],
                "upstream_status": _TERMINAL_STATUS,
                "upstream_status_preserved": True,
                "supplemental_disposition": disposition,
                "evidence_ref": deepcopy(checkpoint["evidence_ref"]),
                "validated_line_axis_count": metrics["validated_line_axis_count"],
                "excluded_empty_line_axis_count": metrics["excluded_empty_line_axis_count"],
                "accepted_line_count": metrics["accepted_line_count"],
                "accepted_word_count": 0,
                "quarantined_subdivision_count": metrics["quarantined_subdivision_count"],
                "word_axes_sha256": evidence["quarantine"]["word_axes_sha256"],
            }
        )
    terminal_count = len(terminal_records)
    accepted_count = dispositions[_ACCEPTED_DISPOSITION]
    rejected_count = dispositions[_REJECTED_DISPOSITION]
    if accepted_count + rejected_count != terminal_count:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only accepted/rejected denominator does not reconcile"
        )
    if validated_line_axis_count != accepted_line_count + excluded_empty_line_axis_count:
        raise WaveOneRoleBLineOnlySupplementError(
            "line-only aggregate line accounting does not reconcile"
        )
    control_payload = _canonical_bytes(control)
    aggregate = {
        "format_version": _AGGREGATE_FORMAT,
        "status": ("COMPLETE_AUTHENTICATED_LINE_ONLY_SUPPLEMENT_FOR_TERMINAL_WORD_BOX_GEOMETRY"),
        "claim_boundary": _CLAIM_BOUNDARY,
        "upstream": {
            "aggregate": {
                "path": "full-reader-aggregate.json",
                "sha256": sha256_bytes(authority.aggregate_payload),
                "size_bytes": len(authority.aggregate_payload),
            },
            "aggregate_identity_sha256": authority.aggregate["aggregate_identity_sha256"],
            "aggregate_status": authority.aggregate["status"],
            "control": {
                "path": "full-reader-execution-control.json",
                "sha256": sha256_bytes(authority.control_payload),
                "size_bytes": len(authority.control_payload),
            },
            "control_identity_sha256": authority.control["control_identity_sha256"],
            "sealed_plan": deepcopy(authority.aggregate["sealed_plan"]),
            "terminal_status": _TERMINAL_STATUS,
            "terminal_failure_reason": _FAILURE_REASON,
            "terminal_denominator_count": terminal_count,
            "status_change_count": 0,
        },
        "control": {
            "identity_sha256": control["control_identity_sha256"],
            "artifact": {
                "path": CONTROL_FILENAME,
                "sha256": sha256_bytes(control_payload),
                "size_bytes": len(control_payload),
            },
        },
        "executor_git": deepcopy(control["executor_git"]),
        "executor_implementation_ledger": deepcopy(control["executor_implementation_ledger"]),
        "page_records": page_records,
        "accounting": {
            "upstream_request_count": 1_449,
            "terminal_denominator_count": terminal_count,
            "supplemental_disposition_count": terminal_count,
            "accepted_page_count": accepted_count,
            "rejected_page_count": rejected_count,
            "accepted_plus_rejected_count": accepted_count + rejected_count,
            "missing_terminal_count": 0,
            "duplicate_terminal_count": 0,
            "foreign_terminal_count": 0,
            "upstream_status_change_count": 0,
            "validated_line_axis_count": validated_line_axis_count,
            "excluded_empty_line_axis_count": excluded_empty_line_axis_count,
            "accepted_line_count": accepted_line_count,
            "accepted_word_count": 0,
            "quarantined_subdivision_count": quarantined_subdivision_count,
            "quarantine_page_hash_count": len(quarantine_hashes),
            "quarantine_page_hashes_sha256": _canonical_sha256(quarantine_hashes),
            "supplemental_disposition_counts": {
                _ACCEPTED_DISPOSITION: accepted_count,
                _REJECTED_DISPOSITION: rejected_count,
            },
            "upstream_terminal_status_counts": {_TERMINAL_STATUS: terminal_count},
            "blank_claim_count": 0,
            "absence_claim_count": 0,
            "statement_classification_count": 0,
            "table_classification_count": 0,
            "row_reconstruction_count": 0,
            "cell_interpretation_count": 0,
            "axis_interpretation_count": 0,
            "schema_mapping_count": 0,
        },
        "safety": _safe_claims(),
    }
    aggregate["aggregate_identity_sha256"] = _canonical_sha256(aggregate)
    return aggregate


def authenticated_line_only_aggregate_is_published(
    project_root: Path, aggregate: Mapping[str, Any]
) -> bool:
    """Read-only authentication of the optional published aggregate artifact."""

    project_root = project_root.resolve()
    relative = OUTPUT_RELATIVE_ROOT / AGGREGATE_FILENAME
    if _relative_entry_is_absent(project_root, relative):
        return False
    payload, _identity = _read_immutable_relative(
        project_root, relative, label="published line-only aggregate"
    )
    published = _json_object(payload, "published line-only aggregate")
    if not _same_typed_json(published, aggregate):
        raise WaveOneRoleBLineOnlySupplementError("published line-only aggregate replay drifted")
    return True


def _verify_with_authority(
    project_root: Path,
    policy: dict[str, Any],
    authority: FinalizedV2Authority,
) -> dict[str, Any]:
    control = _replay_published_control(project_root, policy, authority)
    terminal_records = _terminal_records(authority.aggregate)
    checkpoints, _head = _load_checkpoints(
        project_root,
        control,
        terminal_records,
        create=False,
        recover=False,
    )
    if len(checkpoints) != len(terminal_records):
        raise WaveOneRoleBLineOnlySupplementError("line-only checkpoint denominator is incomplete")
    evidence_records = []
    for upstream, checkpoint in zip(terminal_records, checkpoints, strict=True):
        evidence_records.append(
            _validate_checkpoint_evidence(project_root, authority, control, upstream, checkpoint)
        )
    aggregate = _build_aggregate(
        authority, control, terminal_records, checkpoints, evidence_records
    )
    authenticated_line_only_aggregate_is_published(project_root, aggregate)
    _recheck_upstream_authority(project_root, authority)
    return aggregate


def verify_authenticated_line_only_supplement(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    """Read-only replay of V2 authority, checkpoints, quarantine and line geometry."""

    project_root = project_root.resolve()
    authority = _authenticate_finalized_v2(project_root, model_cache=model_cache.resolve())
    policy = _load_policy(project_root)
    return _verify_with_authority(project_root, policy, authority)


def finalize_authenticated_line_only_supplement(
    project_root: Path, *, model_cache: Path
) -> dict[str, Any]:
    project_root = project_root.resolve()
    policy = _load_policy(project_root)
    _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
    authority = _authenticate_finalized_v2(project_root, model_cache=model_cache.resolve())
    with _execution_lease(project_root):
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        _recover_root_publication_pairs(project_root)
        aggregate = _verify_with_authority(project_root, policy, authority)
        _recheck_upstream_authority(project_root, authority)
        _ensure_capacity(project_root, policy["execution"]["minimum_free_space_bytes"])
        _publish_exclusive(
            project_root,
            OUTPUT_RELATIVE_ROOT,
            AGGREGATE_FILENAME,
            _canonical_bytes(aggregate),
        )
        replay = _verify_with_authority(project_root, policy, authority)
    if not _same_typed_json(replay, aggregate):
        raise WaveOneRoleBLineOnlySupplementError("line-only aggregate changed after publication")
    return aggregate
