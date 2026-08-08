from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
import subprocess
import sys
import types
from dataclasses import replace
from pathlib import Path
from typing import Any

import pytest
import yaml

import bctc_ai.evaluation.e0040_formal_mapping as formal


@pytest.fixture(scope="module")
def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def fresh_subprocess_payload(project_root: Path) -> dict[str, Any]:
    code = """
import sys
from pathlib import Path
from bctc_ai.evaluation.e0040_formal_mapping import _encoded_json, dry_run_e0040_mapping_only
root = Path(sys.argv[1]).resolve()
sys.stdout.buffer.write(_encoded_json(dry_run_e0040_mapping_only(root)))
"""
    completed = subprocess.run(
        [sys.executable, "-c", code, str(project_root)],
        cwd=project_root,
        check=True,
        capture_output=True,
    )
    return json.loads(completed.stdout)


@pytest.fixture(scope="module")
def prerequisites(project_root: Path):
    return formal._load_prerequisites(
        project_root,
        formal.CONTROL_RELATIVE_PATH,
        formal._read_stable_file,
    )


def _mapping_stable(project_root: Path, payload: dict[str, Any]) -> formal._StableFile:
    encoded = formal._encoded_json(payload)
    return formal._StableFile(
        path=project_root / formal.MAPPING_ONLY_RELATIVE_PATH,
        payload=encoded,
        identity=(1, 2, stat_mode_regular(), len(encoded), 3, 4),
        artifact={
            "path": formal.MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "sha256": hashlib.sha256(encoded).hexdigest(),
            "size_bytes": len(encoded),
        },
    )


def stat_mode_regular() -> int:
    return 0o100644


def test_fresh_subprocess_dry_run_is_the_exact_answer_free_challenger(
    fresh_subprocess_payload: dict[str, Any],
):
    payload = fresh_subprocess_payload
    metrics = payload["metrics"]
    assert payload["state"] == formal.MAPPING_ONLY_STATE
    assert metrics == {
        "all_intervals_exhaustive": True,
        "all_pruning_counts_zero": True,
        "base_collision_pair_count": 6,
        "baseline_interval_count": 43,
        "baseline_selected_count": 59,
        "final_interval_count": 44,
        "final_row_status_counts": {
            "NO_ADMISSIBLE_PAIR": 3,
            "RESOLVED_ANCHOR": 43,
            "RESOLVED_PATH": 18,
        },
        "final_selected_count": 61,
        "internal_role_repair_selected_count": 2,
        "mapper_invocation_count": 2,
        "new_collision_pair_count": 0,
        "normalization_changed_schema_node_count": 21,
        "normalization_derived_key_count": 33,
        "result_collision_pair_count": 6,
        "schema_node_count": 77,
        "selected_anchor_count": 43,
        "selected_path_count": 18,
        "source_only_structural_count": 3,
        "source_row_count": 64,
    }
    assert formal._canonical_sha256(payload["challenger_result"]) == (
        formal.CHALLENGER_RESULT_SHA256
    )
    assert payload["result_receipts"]["final_selected_pairs_sha256"] == (formal.FINAL_PAIRS_SHA256)
    assert payload["source_evidence_receipt"]["source_scope_fields_read"] is False
    assert payload["source_evidence_receipt"]["schema_report_norm_ids_sha256"] == (
        formal.SCHEMA_IDS_SHA256
    )
    assert payload["access_contract"]["e0038_or_e0039_mapping_artifact_opened"] is False


def test_e0040_owned_mapper_policy_is_exact_and_formal_ledgers_have_no_forbidden_paths(
    project_root: Path,
):
    policy_path = project_root / formal.MAPPER_POLICY_RELATIVE_PATH
    policy_bytes = policy_path.read_bytes()
    assert hashlib.sha256(policy_bytes).hexdigest() == formal.MAPPER_POLICY_SHA256
    assert len(policy_bytes) == formal.MAPPER_POLICY_SIZE
    assert "e0038" not in formal.MAPPER_POLICY_RELATIVE_PATH.as_posix().casefold()

    control = yaml.safe_load((project_root / formal.CONTROL_RELATIVE_PATH).read_bytes())
    ledgers = [control["input_authority"], control["implementation"]]
    ledgers.append(control["runtime_authority"]["artifacts"])
    forbidden = ("e0038", "e0039", "review", "numeric", "postjoin", "history", "qwen")
    paths = [
        record["path"]
        for ledger in ledgers
        for record in ledger.values()
        if isinstance(record, dict) and "path" in record
    ]
    assert all(not any(token in path.casefold() for token in forbidden) for path in paths)

    tree = ast.parse(
        (project_root / "src/bctc_ai/evaluation/e0040_formal_mapping.py").read_text(
            encoding="utf-8"
        )
    )
    imported = {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert (
        imported
        & {
            "bctc_ai.evaluation.e0037_sealed_mapping",
            "bctc_ai.evaluation.e0038_exact_mapping",
            "bctc_ai.evaluation.e0039_review_packet",
        }
        == set()
    )


@pytest.mark.parametrize(
    "module_name",
    [
        "bctc_ai.evaluation.e0037_sealed_mapping",
        "bctc_ai.evaluation.e0038_exact_mapping",
        "bctc_ai.evaluation.e0039_review_packet",
        "bctc_ai.evaluation.e0041_post_mapping_export",
        "bctc_ai.evaluation.logical_row_label_review_evaluation",
        "bctc_ai.evaluation.numeric_cell_verification",
        "bctc_ai.reference.holdout_labels",
        "bctc_ai.ingestion.mongodb_dump",
        "bctc_ai.ocr.qwen35_logical_row_reader",
    ],
)
def test_process_contamination_guard_rejects_forbidden_preloads(
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
):
    monkeypatch.setitem(sys.modules, module_name, types.ModuleType(module_name))
    with pytest.raises(formal.E0040FormalMappingError, match="contaminated"):
        formal._assert_answer_free_process()


def test_strict_json_and_yaml_reject_duplicate_nonfinite_alias_and_caps(
    monkeypatch: pytest.MonkeyPatch,
):
    with pytest.raises(formal.E0040FormalMappingError, match="strict JSON"):
        formal._decode_json_object(b'{"x":1,"x":2}', "duplicate")
    with pytest.raises(formal.E0040FormalMappingError, match="strict JSON"):
        formal._decode_json_object(b'{"x":NaN}', "nonfinite")
    monkeypatch.setattr(formal, "_MAX_JSON_BYTES", 4)
    with pytest.raises(formal.E0040FormalMappingError, match="byte size"):
        formal._decode_json_object(b'{"x":1}', "oversize")
    with pytest.raises(formal.E0040FormalMappingError, match="decode"):
        formal._decode_control(b"version: 1\nversion: 2\n")
    with pytest.raises(formal.E0040FormalMappingError, match="decode"):
        formal._decode_control(b"left: &x {value: 1}\nright: *x\n")


def test_stable_reader_rejects_final_and_parent_symlinks(tmp_path: Path):
    root = tmp_path.resolve()
    real = root / "real.json"
    real.write_text("{}", encoding="utf-8")
    (root / "linked.json").symlink_to(real)
    with pytest.raises(formal.E0040FormalMappingError, match="cannot open"):
        formal._read_stable_file(root, root / "linked.json", "linked")

    directory = root / "directory"
    directory.mkdir()
    (directory / "item.json").write_text("{}", encoding="utf-8")
    (root / "linked-directory").symlink_to(directory, target_is_directory=True)
    with pytest.raises(formal.E0040FormalMappingError, match="traverse"):
        formal._read_stable_file(
            root,
            root / "linked-directory/item.json",
            "linked parent",
        )


def test_stable_reader_rejects_parent_replacement_even_with_identical_bytes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    directory = root / "evidence"
    directory.mkdir()
    target = directory / "item.json"
    target.write_text('{"same":true}', encoding="utf-8")
    original = formal._open_existing_parent_directory
    calls = 0

    def replace_on_recheck(project_root: Path, relative: Path, label: str):
        nonlocal calls
        calls += 1
        if calls == 2:
            directory.rename(root / "detached-evidence")
            directory.mkdir()
            target.write_text('{"same":true}', encoding="utf-8")
        return original(project_root, relative, label)

    monkeypatch.setattr(formal, "_open_existing_parent_directory", replace_on_recheck)
    with pytest.raises(formal.E0040FormalMappingError, match="canonical identity"):
        formal._read_stable_file(root, target, "parent replacement")


def test_e0037_authority_opens_seal_then_registry_then_mapping(
    project_root: Path,
    prerequisites,
):
    observed: list[str] = []

    def spy_reader(root: Path, path: Path, label: str, **kwargs):
        observed.append(path.relative_to(root).as_posix())
        return formal._read_stable_file(root, path, label, **kwargs)

    authority = formal._load_e0037_authority(project_root, prerequisites, spy_reader)
    assert observed == [
        formal.E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        formal.S3_REGISTRY_RELATIVE_PATH.as_posix(),
        formal.E0037_MAPPING_ONLY_RELATIVE_PATH.as_posix(),
    ]
    assert authority.mapping_stable.artifact["sha256"] == formal.E0037_MAPPING_ONLY_SHA256


def test_invalid_e0037_seal_aborts_before_registry_or_mapping(
    project_root: Path,
    prerequisites,
):
    observed: list[str] = []

    def corrupt_seal(root: Path, path: Path, label: str, **kwargs):
        observed.append(path.relative_to(root).as_posix())
        stable = formal._read_stable_file(root, path, label, **kwargs)
        if path.relative_to(root) == formal.E0037_MAPPING_SEAL_RELATIVE_PATH:
            return replace(
                stable,
                payload=b"{}",
                artifact={
                    "path": formal.E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
                    "sha256": hashlib.sha256(b"{}").hexdigest(),
                    "size_bytes": 2,
                },
            )
        return stable

    with pytest.raises(formal.E0040FormalMappingError, match="pinned identity"):
        formal._load_e0037_authority(project_root, prerequisites, corrupt_seal)
    assert observed == [formal.E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix()]


def test_duplicated_s3_record_aborts_before_mapping_open(
    project_root: Path,
    prerequisites,
):
    expected = prerequisites.control["input_authority"]["s3_snapshot"]
    registry = (project_root / formal.S3_REGISTRY_RELATIVE_PATH).read_bytes()
    matching = next(
        line
        for line in registry.splitlines(keepends=True)
        if formal.S3_SNAPSHOT_ID.encode() in line
    )
    duplicated = registry + matching
    with pytest.raises(formal.E0040FormalMappingError, match="duplicated"):
        formal._load_unique_s3_record(duplicated, expected)

    observed: list[str] = []

    def inject_duplicate(root: Path, path: Path, label: str, **kwargs):
        observed.append(path.relative_to(root).as_posix())
        stable = formal._read_stable_file(root, path, label, **kwargs)
        if path.relative_to(root) == formal.S3_REGISTRY_RELATIVE_PATH:
            # The injected reader models a coordinated descriptor seam; the
            # registry parser must still reject duplication before mapping open.
            return replace(stable, payload=duplicated)
        return stable

    with pytest.raises(formal.E0040FormalMappingError, match="duplicated"):
        formal._load_e0037_authority(project_root, prerequisites, inject_duplicate)
    assert observed == [
        formal.E0037_MAPPING_SEAL_RELATIVE_PATH.as_posix(),
        formal.S3_REGISTRY_RELATIVE_PATH.as_posix(),
    ]


def _mutate_mapping(payload: dict[str, Any], case: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if case == "extra_top_level":
        mutated["unexpected"] = True
    elif case == "state":
        mutated["state"] = "FORGED"
    elif case == "input_ledger":
        mutated["input_hash_ledger"]["control"]["sha256"] = "0" * 64
    elif case == "implementation_ledger":
        mutated["implementation_hash_ledger"]["mapper"]["size_bytes"] += 1
    elif case == "runtime":
        mutated["runtime_versions"]["python"] = "0.0.0"
    elif case == "e0037_receipt":
        mutated["e0037_authority_receipt"]["restore_verified"] = False
    elif case == "source_receipt":
        mutated["source_evidence_receipt"]["source_scope_fields_read"] = True
    elif case == "coordinated_challenger_digest":
        mutated["challenger_result"]["final_selected_pairs"][0][1] += 1
        challenger_bytes = formal._canonical_compact_bytes(mutated["challenger_result"])
        mutated["result_receipts"]["challenger_result_sha256"] = hashlib.sha256(
            challenger_bytes
        ).hexdigest()
        mutated["result_receipts"]["challenger_result_size_bytes"] = len(challenger_bytes)
    elif case == "metrics":
        mutated["metrics"]["baseline_interval_count"] = 44
    elif case == "access":
        mutated["access_contract"]["history_or_mongodb_opened"] = True
    elif case == "limitations":
        mutated["limitations"] = []
    elif case == "authority":
        mutated["authority"]["mapping_accuracy"] = True
    elif case == "claim":
        mutated["claim_boundary"] += " forged"
    else:  # pragma: no cover - protects the mutation table itself
        raise AssertionError(case)
    return mutated


@pytest.mark.parametrize(
    "case",
    [
        "extra_top_level",
        "state",
        "input_ledger",
        "implementation_ledger",
        "runtime",
        "e0037_receipt",
        "source_receipt",
        "coordinated_challenger_digest",
        "metrics",
        "access",
        "limitations",
        "authority",
        "claim",
    ],
)
def test_mapping_payload_validator_rejects_every_authority_surface_mutation(
    project_root: Path,
    prerequisites,
    fresh_subprocess_payload: dict[str, Any],
    case: str,
):
    mutated = _mutate_mapping(fresh_subprocess_payload, case)
    with pytest.raises(formal.E0040FormalMappingError):
        formal._validate_mapping_before_replay(
            mutated,
            prerequisites,
            expected_git_commit=fresh_subprocess_payload["capture_git_commit"],
            encoded_bytes=formal._encoded_json(mutated),
        )


def test_mapping_payload_validator_accepts_exact_builder_payload(
    prerequisites,
    fresh_subprocess_payload: dict[str, Any],
):
    formal._validate_mapping_before_replay(
        fresh_subprocess_payload,
        prerequisites,
        expected_git_commit=fresh_subprocess_payload["capture_git_commit"],
        encoded_bytes=formal._encoded_json(fresh_subprocess_payload),
    )


def _mutate_seal(payload: dict[str, Any], case: str) -> dict[str, Any]:
    mutated = copy.deepcopy(payload)
    if case == "extra_top_level":
        mutated["unexpected"] = True
    elif case == "commit":
        mutated["seal_git_commit"] = "0" * 40
    elif case == "inventory":
        mutated["inventory"]["file_count"] = 2
    elif case == "metrics":
        mutated["metrics"]["final_selected_count"] = 60
    elif case == "result_receipts":
        mutated["result_receipts"]["final_result_sha256"] = "0" * 64
    elif case == "ledger":
        mutated["input_hash_ledger"]["mapping_only"]["size_bytes"] += 1
    elif case == "replay":
        mutated["replay"]["exact_canonical_byte_equality"] = False
    elif case == "access":
        mutated["access_contract"]["review_or_steward_answers_opened"] = True
    elif case == "authority":
        mutated["authority"]["mapping_accuracy"] = True
    elif case == "claim":
        mutated["claim_boundary"] += " forged"
    else:  # pragma: no cover
        raise AssertionError(case)
    return mutated


@pytest.mark.parametrize(
    "case",
    [
        "extra_top_level",
        "commit",
        "inventory",
        "metrics",
        "result_receipts",
        "ledger",
        "replay",
        "access",
        "authority",
        "claim",
    ],
)
def test_mapping_seal_validator_rejects_every_seal_surface_mutation(
    project_root: Path,
    prerequisites,
    fresh_subprocess_payload: dict[str, Any],
    case: str,
):
    stable = _mapping_stable(project_root, fresh_subprocess_payload)
    seal = formal._assemble_mapping_seal(
        commit=fresh_subprocess_payload["capture_git_commit"],
        control_stable=prerequisites.control_stable,
        mapping_stable=stable,
        mapping_payload=fresh_subprocess_payload,
    )
    with pytest.raises(formal.E0040FormalMappingError):
        formal._validate_mapping_seal_payload(
            _mutate_seal(seal, case),
            prerequisites,
            mapping_stable=stable,
            mapping_payload=fresh_subprocess_payload,
            expected_git_commit=fresh_subprocess_payload["capture_git_commit"],
        )


def test_mapping_seal_validator_accepts_exact_deterministic_seal(
    project_root: Path,
    prerequisites,
    fresh_subprocess_payload: dict[str, Any],
):
    stable = _mapping_stable(project_root, fresh_subprocess_payload)
    seal = formal._assemble_mapping_seal(
        commit=fresh_subprocess_payload["capture_git_commit"],
        control_stable=prerequisites.control_stable,
        mapping_stable=stable,
        mapping_payload=fresh_subprocess_payload,
    )
    formal._validate_mapping_seal_payload(
        seal,
        prerequisites,
        mapping_stable=stable,
        mapping_payload=fresh_subprocess_payload,
        expected_git_commit=fresh_subprocess_payload["capture_git_commit"],
    )


def test_exclusive_publication_refuses_overwrite_and_preserves_existing_bytes(tmp_path: Path):
    root = tmp_path.resolve()
    directory = root / "out"
    directory.mkdir()
    output = directory / "artifact.json"
    output.write_bytes(b"existing")
    with pytest.raises(formal.E0040FormalMappingError, match="refusing to overwrite"):
        formal._exclusive_publish_json(
            root,
            output,
            {"value": 1},
            exclusive_parent_inventory=("artifact.json",),
        )
    assert output.read_bytes() == b"existing"
    assert tuple(path.name for path in directory.iterdir()) == ("artifact.json",)


def test_publication_parent_replacement_is_detected_and_created_link_is_rolled_back(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    output = root / "out/artifact.json"
    original = formal._open_existing_parent_directory
    calls = 0

    def replace_parent(project_root: Path, relative: Path, label: str):
        nonlocal calls
        calls += 1
        if calls == 1:
            (root / "out/artifact.json").write_bytes(b"same inode but changed size")
            (root / "out").rename(root / "detached")
            (root / "out").mkdir()
            (root / "out/sentinel").write_text("unrelated", encoding="utf-8")
        return original(project_root, relative, label)

    monkeypatch.setattr(formal, "_open_existing_parent_directory", replace_parent)
    with pytest.raises(formal.E0040FormalMappingError, match="publication"):
        formal._exclusive_publish_json(
            root,
            output,
            {"value": 1},
            exclusive_parent_inventory=("artifact.json",),
        )
    assert not (root / "detached/artifact.json").exists()
    assert (root / "out/sentinel").read_text(encoding="utf-8") == "unrelated"


def test_final_same_name_replacement_never_returns_success_or_deletes_replacement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    output = root / "out/artifact.json"
    original = formal._open_existing_parent_directory

    def replace_final_file(project_root: Path, relative: Path, label: str):
        parent, final_name = original(project_root, relative, label)
        if label == "E-0040 final publication inventory":
            os.unlink(final_name, dir_fd=parent)
            descriptor = os.open(
                final_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o644,
                dir_fd=parent,
            )
            try:
                os.write(descriptor, b"FORGED")
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            os.fsync(parent)
        return parent, final_name

    monkeypatch.setattr(formal, "_open_existing_parent_directory", replace_final_file)
    with pytest.raises(formal.E0040FormalMappingError):
        formal._exclusive_publish_json(
            root,
            output,
            {"value": 1},
            exclusive_parent_inventory=("artifact.json",),
        )
    assert output.read_bytes() == b"FORGED"


def test_capture_has_no_fallible_post_publication_inventory_observer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    published = False
    inventory_calls: list[bool] = []

    def inventory(_root: Path, *, require_mapping: bool):
        inventory_calls.append(require_mapping)
        if published:
            raise AssertionError("post-publication observer must not run")
        return ()

    def publish(*_args, **_kwargs):
        nonlocal published
        published = True
        return "0" * 64

    monkeypatch.setattr(formal, "_assert_answer_free_process", lambda: None)
    monkeypatch.setattr(formal, "_mapping_output_inventory", inventory)
    monkeypatch.setattr(formal, "_clean_git_commit", lambda _root: "1" * 40)
    monkeypatch.setattr(formal, "build_e0040_mapping_only", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(formal, "_recheck_payload_ledgers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        formal, "_assert_payload_ledgers_match_head", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(formal, "_exclusive_publish_json", publish)
    assert formal.capture_e0040_mapping_only(root) == {}
    assert inventory_calls == [False]
    assert published is True


def test_mapping_capture_rechecks_ignored_inputs_after_final_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    commit = "1" * 40
    clean_calls = 0
    ignored_input_mutated = False
    published = False

    def clean(_root: Path):
        nonlocal clean_calls, ignored_input_mutated
        clean_calls += 1
        if clean_calls == 2:
            ignored_input_mutated = True
        return commit

    def recheck(*_args, **_kwargs):
        if ignored_input_mutated:
            raise formal.E0040FormalMappingError("ignored input drifted")

    def publish(*_args, **_kwargs):
        nonlocal published
        published = True

    monkeypatch.setattr(formal, "_assert_answer_free_process", lambda: None)
    monkeypatch.setattr(formal, "_mapping_output_inventory", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(formal, "_clean_git_commit", clean)
    monkeypatch.setattr(formal, "build_e0040_mapping_only", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(formal, "_recheck_payload_ledgers", recheck)
    monkeypatch.setattr(
        formal, "_assert_payload_ledgers_match_head", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(formal, "_exclusive_publish_json", publish)
    with pytest.raises(formal.E0040FormalMappingError, match="ignored input drifted"):
        formal.capture_e0040_mapping_only(root)
    assert published is False


def test_seal_capture_has_no_fallible_post_publication_observer(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    published = False
    inventory_calls: list[bool] = []
    commit = "1" * 40
    mapping_payload = {"capture_git_commit": commit}
    mapping_stable = formal._StableFile(
        path=root / formal.MAPPING_ONLY_RELATIVE_PATH,
        payload=b"{}",
        identity=(1, 2, stat_mode_regular(), 2, 3, 4),
        artifact={
            "path": formal.MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "sha256": hashlib.sha256(b"{}").hexdigest(),
            "size_bytes": 2,
        },
    )

    def inventory(_root: Path, *, require_mapping: bool):
        inventory_calls.append(require_mapping)
        if published:
            raise AssertionError("post-publication observer must not run")
        return (formal.MAPPING_ONLY_RELATIVE_PATH.name,)

    def publish(*_args, **_kwargs):
        nonlocal published
        published = True
        return "0" * 64

    monkeypatch.setattr(formal, "_assert_answer_free_process", lambda: None)
    monkeypatch.setattr(formal, "_clean_git_commit", lambda _root: commit)
    monkeypatch.setattr(formal, "_mapping_output_inventory", inventory)
    monkeypatch.setattr(
        formal,
        "_load_prerequisites",
        lambda *_args, **_kwargs: types.SimpleNamespace(control_stable=None),
    )
    monkeypatch.setattr(formal, "_stable_read", lambda *_args, **_kwargs: mapping_stable)
    monkeypatch.setattr(formal, "_decode_json_object", lambda *_args, **_kwargs: mapping_payload)
    monkeypatch.setattr(formal, "_validate_mapping_before_replay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        formal, "build_e0040_mapping_only", lambda *_args, **_kwargs: mapping_payload
    )
    monkeypatch.setattr(formal, "_assert_exact_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_encoded_json", lambda _payload: b"{}")
    monkeypatch.setattr(formal, "_assemble_mapping_seal", lambda **_kwargs: {"seal": True})
    monkeypatch.setattr(formal, "_assert_finite_tree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_validate_mapping_seal_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_assert_unchanged", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_recheck_payload_ledgers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        formal, "_assert_payload_ledgers_match_head", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(formal, "_exclusive_publish_json", publish)
    assert formal.capture_e0040_mapping_seal(root) == {"seal": True}
    assert inventory_calls == [True, True]
    assert published is True


def test_seal_rechecks_ignored_mapping_after_final_clean(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    root = tmp_path.resolve()
    commit = "1" * 40
    mapping_payload = {"capture_git_commit": commit}
    mapping_stable = formal._StableFile(
        path=root / formal.MAPPING_ONLY_RELATIVE_PATH,
        payload=b"{}",
        identity=(1, 2, stat_mode_regular(), 2, 3, 4),
        artifact={
            "path": formal.MAPPING_ONLY_RELATIVE_PATH.as_posix(),
            "sha256": hashlib.sha256(b"{}").hexdigest(),
            "size_bytes": 2,
        },
    )
    clean_calls = 0
    ignored_mapping_mutated = False
    published = False

    def clean(_root: Path):
        nonlocal clean_calls, ignored_mapping_mutated
        clean_calls += 1
        if clean_calls == 2:
            ignored_mapping_mutated = True
        return commit

    def unchanged(*_args, **_kwargs):
        if ignored_mapping_mutated:
            raise formal.E0040FormalMappingError("ignored mapping drifted")

    def publish(*_args, **_kwargs):
        nonlocal published
        published = True

    monkeypatch.setattr(formal, "_assert_answer_free_process", lambda: None)
    monkeypatch.setattr(
        formal,
        "_mapping_output_inventory",
        lambda *_args, **_kwargs: (formal.MAPPING_ONLY_RELATIVE_PATH.name,),
    )
    monkeypatch.setattr(formal, "_clean_git_commit", clean)
    monkeypatch.setattr(
        formal,
        "_load_prerequisites",
        lambda *_args, **_kwargs: types.SimpleNamespace(control_stable=None),
    )
    monkeypatch.setattr(formal, "_stable_read", lambda *_args, **_kwargs: mapping_stable)
    monkeypatch.setattr(formal, "_decode_json_object", lambda *_args, **_kwargs: mapping_payload)
    monkeypatch.setattr(formal, "_validate_mapping_before_replay", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        formal, "build_e0040_mapping_only", lambda *_args, **_kwargs: mapping_payload
    )
    monkeypatch.setattr(formal, "_assert_exact_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_encoded_json", lambda _payload: b"{}")
    monkeypatch.setattr(formal, "_assemble_mapping_seal", lambda **_kwargs: {"seal": True})
    monkeypatch.setattr(formal, "_assert_finite_tree", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_validate_mapping_seal_payload", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(formal, "_assert_unchanged", unchanged)
    monkeypatch.setattr(formal, "_recheck_payload_ledgers", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        formal, "_assert_payload_ledgers_match_head", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(formal, "_exclusive_publish_json", publish)
    with pytest.raises(formal.E0040FormalMappingError, match="ignored mapping drifted"):
        formal.capture_e0040_mapping_seal(root)
    assert published is False


def test_git_environment_is_sanitized_and_clean_gate_rejects_untracked_and_index_flags(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    monkeypatch.setenv("GIT_DIR", "/forbidden")
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "core.fsmonitor")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "malicious")
    sanitized = formal._sanitized_git_environment()
    allowed_git_keys = {"GIT_CONFIG_NOSYSTEM", "GIT_CONFIG_GLOBAL"}
    assert not any(key.startswith("GIT_") for key in sanitized if key not in allowed_git_keys)
    assert sanitized["GIT_CONFIG_NOSYSTEM"] == "1"
    assert sanitized["GIT_CONFIG_GLOBAL"] == os.devnull
    for key in ("GIT_DIR", "GIT_CONFIG_COUNT", "GIT_CONFIG_KEY_0", "GIT_CONFIG_VALUE_0"):
        monkeypatch.delenv(key)

    root = tmp_path.resolve()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True
    )
    tracked = root / "tracked.txt"
    tracked.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
    (root / "untracked.txt").write_text("x", encoding="utf-8")
    with pytest.raises(formal.E0040FormalMappingError, match="clean Git worktree"):
        formal._clean_git_commit(root)
    (root / "untracked.txt").unlink()

    subprocess.run(
        ["git", "-C", str(root), "update-index", "--assume-unchanged", "tracked.txt"],
        check=True,
    )
    with pytest.raises(formal.E0040FormalMappingError, match="non-normal Git index"):
        formal._clean_git_commit(root)
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--no-assume-unchanged", "tracked.txt"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--skip-worktree", "tracked.txt"],
        check=True,
    )
    with pytest.raises(formal.E0040FormalMappingError, match="non-normal Git index"):
        formal._clean_git_commit(root)


def test_head_blob_binding_rejects_coordinated_worktree_and_record_mutation(tmp_path: Path):
    root = tmp_path.resolve()
    subprocess.run(["git", "init", "-q", str(root)], check=True)
    subprocess.run(["git", "-C", str(root), "config", "user.name", "test"], check=True)
    subprocess.run(
        ["git", "-C", str(root), "config", "user.email", "test@example.invalid"], check=True
    )
    tracked = root / "tracked.txt"
    tracked.write_text("original\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(root), "add", "tracked.txt"], check=True)
    subprocess.run(["git", "-C", str(root), "commit", "-qm", "base"], check=True)
    stable = formal._read_stable_file(root, tracked, "tracked")
    formal._assert_tracked_record_matches_head(
        root,
        stable.artifact,
        name="tracked",
        expected_path=Path("tracked.txt"),
    )
    tracked.write_text("coordinated mutation\n", encoding="utf-8")
    mutated = formal._read_stable_file(root, tracked, "mutated")
    with pytest.raises(formal.E0040FormalMappingError, match="HEAD blob"):
        formal._assert_tracked_record_matches_head(
            root,
            mutated.artifact,
            name="tracked",
            expected_path=Path("tracked.txt"),
        )


def test_canonical_path_and_mapping_inventory_fail_closed(tmp_path: Path):
    root = tmp_path.resolve()
    with pytest.raises(formal.E0040FormalMappingError, match="canonical path"):
        formal._canonical_input_path(
            root,
            Path("elsewhere.json"),
            formal.MAPPING_ONLY_RELATIVE_PATH,
            "mapping",
        )
    directory = root / formal.MAPPING_ONLY_RELATIVE_PATH.parent
    directory.mkdir(parents=True)
    (directory / "unexpected").write_text("x", encoding="utf-8")
    with pytest.raises(formal.E0040FormalMappingError, match="exact required inventory"):
        formal._mapping_output_inventory(root, require_mapping=False)
