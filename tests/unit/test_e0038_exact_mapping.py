from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

from bctc_ai.evaluation import e0038_exact_mapping as exact_mapping
from bctc_ai.evaluation.e0038_exact_mapping import (
    CONTROL_RELATIVE_PATH,
    MAPPING_ONLY_RELATIVE_PATH,
    MAPPING_SEAL_RELATIVE_PATH,
    E0038ExactMappingError,
    _assemble_mapping_seal,
    _assert_tracked_record_matches_head,
    _clean_git_commit,
    _decode_control,
    _decode_json_object,
    _exclusive_publish_json,
    _load_unique_s3_record,
    _mapping_output_inventory,
    _StableFile,
    _validate_e0037_seal_before_mapping_open,
    build_e0038_mapping_only,
)


def _control(project_root: Path) -> dict[str, object]:
    return _decode_control((project_root / CONTROL_RELATIVE_PATH).read_bytes())


def _stable(path: Path, relative: Path, payload: bytes) -> _StableFile:
    return _StableFile(
        path=path,
        payload=payload,
        identity=(1, 2, 0o100644, len(payload), 3, 4),
        artifact={
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        },
    )


def _init_git_repository(path: Path, *, filename: str = "tracked.txt") -> str:
    path.mkdir(parents=True, exist_ok=True)
    subprocess.run(["git", "init", "-q", str(path)], check=True)
    subprocess.run(["git", "-C", str(path), "config", "user.name", "E0038 test"], check=True)
    subprocess.run(
        ["git", "-C", str(path), "config", "user.email", "e0038@example.invalid"],
        check=True,
    )
    (path / filename).write_text("alpha", encoding="utf-8")
    subprocess.run(["git", "-C", str(path), "add", filename], check=True)
    subprocess.run(["git", "-C", str(path), "commit", "-qm", "fixture"], check=True)
    return subprocess.run(
        ["git", "-C", str(path), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def test_control_pins_every_input_and_implementation_and_keeps_claims_bounded(
    project_root: Path,
):
    control = _control(project_root)

    for section in ("input_authority", "implementation"):
        for name, record in control[section].items():
            if name == "s3_snapshot":
                continue
            path = project_root / record["path"]
            payload = path.read_bytes()
            assert record == {
                "path": path.relative_to(project_root).as_posix(),
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }, name
    for name, record in control["runtime_authority"]["artifacts"].items():
        path = project_root / record["path"]
        payload = path.read_bytes()
        assert record == {
            "path": path.relative_to(project_root).as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }, name
    assert control["runtime_authority"]["versions"] == exact_mapping._RUNTIME_VERSIONS

    contract = control["mapping_contract"]
    assert contract["base_projection_sha256"] == exact_mapping.BASE_PROJECTION_SHA256
    assert contract["result_projection_sha256"] == exact_mapping.RESULT_PROJECTION_SHA256
    assert contract["changed_report_norm_ids"] == [4375, 5699]
    assert contract["actual_generated_and_retained_states_recorded"] is True
    assert (
        contract["exact_search_resource_cap_semantics"]
        == "RETAINED_SIGNATURE_CERTIFICATE_BOUND_NOT_GENERATED_STATE_OR_TOTAL_COMPUTE_CAP"
    )
    assert contract["raw_projection_published"] is False
    assert contract["raw_core_result_published_without_overlay_receipt"] is False
    claims = " ".join(control["claim_boundaries"].values()).casefold()
    assert "calibration" in claims
    assert "not schema authority" in claims
    assert "production readiness" in claims


def test_control_loader_rejects_duplicate_keys_and_recursive_aliases():
    with pytest.raises(E0038ExactMappingError, match="cannot decode"):
        _decode_control(b"version: 1\nversion: 2\n")
    with pytest.raises(E0038ExactMappingError, match="cannot decode"):
        _decode_control(b"loop: &loop [*loop]\n")


@pytest.mark.parametrize(
    "payload",
    [b'{"a":1,"a":2}', b'{"value":NaN}', b'{"value":Infinity}'],
)
def test_json_loader_rejects_duplicate_keys_and_nonfinite_values(payload: bytes):
    with pytest.raises(E0038ExactMappingError, match="strict JSON"):
        _decode_json_object(payload, "fixture")


def test_s3_registry_requires_one_byte_exact_restore_pass_record(project_root: Path):
    control = _control(project_root)
    expected = control["input_authority"]["s3_snapshot"]
    registry = (project_root / exact_mapping.S3_REGISTRY_RELATIVE_PATH).read_bytes()

    assert _load_unique_s3_record(registry, expected) == expected
    duplicate = registry + json.dumps(expected, sort_keys=True).encode("utf-8") + b"\n"
    with pytest.raises(E0038ExactMappingError, match="duplicated"):
        _load_unique_s3_record(duplicate, expected)


@pytest.mark.parametrize(
    ("tampered_label", "tamper_payload"),
    [
        ("E-0038 implementation exact_search_helper", False),
        ("E-0037 mapping seal", True),
        ("S3 artifact snapshot registry", True),
    ],
)
def test_prerequisite_tamper_fails_before_mapping_bytes_are_opened(
    project_root: Path,
    tampered_label: str,
    tamper_payload: bool,
):
    opened: list[str] = []

    def reader(root, path, label, **kwargs):
        stable = exact_mapping._read_stable_file(root, path, label, **kwargs)
        opened.append(label)
        if label != tampered_label:
            return stable
        if tamper_payload:
            return replace(stable, payload=b"{}")
        artifact = {**stable.artifact, "sha256": "0" * 64}
        return replace(stable, artifact=artifact)

    with pytest.raises(E0038ExactMappingError):
        build_e0038_mapping_only(
            project_root,
            capture_git_commit="a" * 40,
            _reader=reader,
        )
    assert "E-0037 mapping-only bytes" not in opened


def test_e0037_seal_requires_capture_and_seal_commit_equality(project_root: Path):
    control = _control(project_root)
    seal = json.loads((project_root / exact_mapping.E0037_MAPPING_SEAL_RELATIVE_PATH).read_text())
    seal["mapping_capture_git_commit"] = "a" * 40
    assert seal["mapping_capture_git_commit"] != seal["seal_git_commit"]

    with pytest.raises(E0038ExactMappingError, match="identity"):
        _validate_e0037_seal_before_mapping_open(seal, control)


def test_mapping_sealer_has_exact_one_file_inventory_and_false_authorities(tmp_path: Path):
    commit = "a" * 40
    control_payload = b"control"
    mapping_payload = {
        "capture_git_commit": commit,
        "exact_mapping_bundle": {"exact_search": {"status": "EXACT_SEARCH_COMPLETE"}},
        "input_hash_ledger": {},
        "implementation_hash_ledger": {},
        "runtime_hash_ledger": {},
        "runtime_versions": dict(exact_mapping._RUNTIME_VERSIONS),
    }
    mapping_bytes = exact_mapping._encoded_json(mapping_payload)
    control_stable = _stable(
        tmp_path / CONTROL_RELATIVE_PATH,
        CONTROL_RELATIVE_PATH,
        control_payload,
    )
    mapping_stable = _stable(
        tmp_path / MAPPING_ONLY_RELATIVE_PATH,
        MAPPING_ONLY_RELATIVE_PATH,
        mapping_bytes,
    )
    seal = _assemble_mapping_seal(
        commit=commit,
        control_stable=control_stable,
        mapping_stable=mapping_stable,
        mapping_payload=mapping_payload,
    )

    assert seal["inventory"] == {"file_count": 1, "files": [mapping_stable.artifact]}
    assert seal["replay"]["exact_byte_equality"] is True
    assert all(
        value is False
        for key, value in seal["authority"].items()
        if key not in {"exact_one_file_hash_identity", "deterministic_replay_byte_identity"}
    )


def test_git_clean_check_ignores_hostile_environment_and_local_status_config(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    real = tmp_path / "real"
    fake = tmp_path / "fake"
    real_commit = _init_git_repository(real)
    _init_git_repository(fake, filename="fake.txt")
    monkeypatch.setenv("GIT_DIR", str(fake / ".git"))
    monkeypatch.setenv("GIT_WORK_TREE", str(fake))
    monkeypatch.setenv("GIT_CONFIG_COUNT", "1")
    monkeypatch.setenv("GIT_CONFIG_KEY_0", "status.showUntrackedFiles")
    monkeypatch.setenv("GIT_CONFIG_VALUE_0", "no")

    assert exact_mapping._git_commit(real) == real_commit
    subprocess.run(
        ["git", "-C", str(real), "config", "status.showUntrackedFiles", "no"],
        check=True,
    )
    (real / "hidden.txt").write_text("must be detected", encoding="utf-8")
    with pytest.raises(E0038ExactMappingError, match="clean Git worktree"):
        _clean_git_commit(real)


def test_git_clean_check_rejects_skip_worktree_and_head_blob_drift(tmp_path: Path):
    root = tmp_path / "repo"
    _init_git_repository(root)
    tracked = root / "tracked.txt"
    payload = tracked.read_bytes()
    original_record = _stable(tracked, Path("tracked.txt"), payload).artifact
    _assert_tracked_record_matches_head(
        root,
        original_record,
        name="fixture",
        expected_path=Path("tracked.txt"),
    )

    tracked.write_text("bravo", encoding="utf-8")
    tampered = tracked.read_bytes()
    tampered_record = _stable(tracked, Path("tracked.txt"), tampered).artifact
    with pytest.raises(E0038ExactMappingError, match="HEAD blob"):
        _assert_tracked_record_matches_head(
            root,
            tampered_record,
            name="fixture",
            expected_path=Path("tracked.txt"),
        )
    tracked.write_bytes(payload)
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--skip-worktree", "tracked.txt"],
        check=True,
    )
    with pytest.raises(E0038ExactMappingError, match="index flags"):
        _clean_git_commit(root)
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--no-skip-worktree", "tracked.txt"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(root), "update-index", "--assume-unchanged", "tracked.txt"],
        check=True,
    )
    with pytest.raises(E0038ExactMappingError, match="index flags"):
        _clean_git_commit(root)


def test_publisher_rolls_back_if_parent_is_renamed_after_link(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    target = tmp_path / "out/artifact.json"
    original_link = exact_mapping.os.link

    def racing_link(*args, **kwargs):
        original_link(*args, **kwargs)
        (tmp_path / "out").rename(tmp_path / "detached")
        (tmp_path / "out").mkdir()

    monkeypatch.setattr(exact_mapping.os, "link", racing_link)
    with pytest.raises(E0038ExactMappingError, match="publication"):
        _exclusive_publish_json(
            tmp_path,
            target,
            {"fixture": True},
            exclusive_parent_inventory=("artifact.json",),
        )
    assert not target.exists()
    assert not (tmp_path / "detached/artifact.json").exists()


def test_stable_reader_rejects_parent_rename_even_when_replacement_bytes_match(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    source = tmp_path / "input/payload.json"
    source.parent.mkdir()
    source.write_bytes(b"{}")
    inherited = exact_mapping._read_stable_file_e0037

    def racing_read(*args, **kwargs):
        stable = inherited(*args, **kwargs)
        (tmp_path / "input").rename(tmp_path / "detached-input")
        (tmp_path / "input").mkdir()
        (tmp_path / "input/payload.json").write_bytes(stable.payload)
        return stable

    monkeypatch.setattr(exact_mapping, "_read_stable_file_e0037", racing_read)
    with pytest.raises(E0038ExactMappingError, match="fresh canonical identity"):
        exact_mapping._read_stable_file(tmp_path, source, "racing fixture")


def test_mapping_inventory_rejects_ignored_extra_file(tmp_path: Path):
    directory = tmp_path / exact_mapping.MAPPING_ONLY_RELATIVE_PATH.parent
    directory.mkdir(parents=True)
    (directory / "extra.bin").write_bytes(b"extra")
    with pytest.raises(E0038ExactMappingError, match="one-file inventory"):
        _mapping_output_inventory(tmp_path, require_mapping=False)


def test_formal_capture_clean_git_failure_preserves_published_artifacts(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    output = project_root / MAPPING_ONLY_RELATIVE_PATH
    seal = project_root / MAPPING_SEAL_RELATIVE_PATH
    output_before = output.read_bytes()
    seal_before = seal.read_bytes()
    assert len(output_before) == 646_606
    assert hashlib.sha256(output_before).hexdigest() == (
        "8b1074d2ca57efcb1c6da123615ace86438069b4d581b9afb4b6e4cfbf01a9e9"
    )
    assert len(seal_before) == 6_421
    assert hashlib.sha256(seal_before).hexdigest() == (
        "bffcaf56d80af458187a646269862b8bf669237d865fa1561ab41b056db06137"
    )
    monkeypatch.setattr(exact_mapping, "_mapping_output_inventory", lambda *_args, **_kwargs: ())
    monkeypatch.setattr(
        exact_mapping,
        "_clean_git_commit",
        lambda _root: (_ for _ in ()).throw(E0038ExactMappingError("dirty fixture")),
    )

    with pytest.raises(E0038ExactMappingError, match="dirty fixture"):
        exact_mapping.capture_e0038_mapping_only(project_root)
    assert output.read_bytes() == output_before
    assert seal.read_bytes() == seal_before
