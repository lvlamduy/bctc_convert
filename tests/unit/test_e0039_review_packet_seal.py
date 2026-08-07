from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

from bctc_ai.evaluation import e0038_exact_mapping as exact_mapping
from bctc_ai.evaluation import e0039_review_packet as packet
from bctc_ai.evaluation import e0039_review_packet_seal as seal
from bctc_ai.evaluation.e0039_review_packet_seal import (
    E0039ReviewPacketSealError,
    capture_e0039_review_packet_seal,
)

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
SEAL_HEAD = "b" * 40
FIXTURE_FILES = tuple(
    sorted(
        {
            seal.CONTROL_RELATIVE_PATH,
            *seal._FROZEN_PATHS.values(),
            *seal._IMPLEMENTATION_PATHS.values(),
        },
        key=Path.as_posix,
    )
)


@pytest.fixture(autouse=True)
def _isolate_seal_tests_from_unrelated_review_test_collection():
    prefixes = seal._FORBIDDEN_REVIEW_MODULE_PREFIXES
    saved = {
        name: module
        for name, module in tuple(sys.modules.items())
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes)
    }
    for name in saved:
        sys.modules.pop(name, None)
    yield
    for name in tuple(sys.modules):
        if any(name == prefix or name.startswith(f"{prefix}.") for prefix in prefixes):
            sys.modules.pop(name, None)
    sys.modules.update(saved)


def _copy_fixture(tmp_path: Path) -> Path:
    root = tmp_path / "project"
    for relative in FIXTURE_FILES:
        destination = root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(REPOSITORY_ROOT / relative, destination)
    return root


def _allow_fixture_git(monkeypatch: pytest.MonkeyPatch) -> dict[str, list[str]]:
    calls = {"ancestor": [], "head": [], "capture": []}
    monkeypatch.setattr(seal, "_clean_git_commit", lambda _root: SEAL_HEAD)

    def record_ancestor(_root: Path, capture: str, current: str) -> None:
        calls["ancestor"].append(f"{capture}:{current}")

    def record_head(
        _root: Path,
        _record: object,
        *,
        name: str,
        path: Path,
        reader: object,
    ) -> None:
        del path, reader
        calls["head"].append(name)

    def record_capture(
        _root: Path,
        _record: object,
        *,
        name: str,
        expected_path: Path,
        commit: str,
    ) -> None:
        del expected_path, commit
        calls["capture"].append(name)

    monkeypatch.setattr(seal, "_assert_capture_commit_ancestor", record_ancestor)
    monkeypatch.setattr(seal, "_head_bind", record_head)
    monkeypatch.setattr(seal, "_assert_record_matches_git_commit", record_capture)
    return calls


def _capture_fixture(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, dict[str, object]]:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    result = capture_e0039_review_packet_seal(root)
    return root, result


def _validation_arguments(result: dict[str, object]) -> dict[str, object]:
    ledger = result["input_hash_ledger"]
    inventory = result["inventory"]
    return {
        "expected_seal_commit": result["seal_git_commit"],
        "expected_control_artifact": ledger["seal_control"],
        "expected_seal_implementation": ledger["seal_implementation"],
        "expected_packet_control_artifact": ledger["packet_control"],
        "expected_packet_implementation": ledger["packet_implementation"],
        "expected_packet_artifact": inventory["files"][0],
    }


def _replace_fixture_packet(
    root: Path,
    monkeypatch: pytest.MonkeyPatch,
    payload: bytes,
) -> None:
    packet_path = root / seal.PACKET_RELATIVE_PATH
    packet_path.write_bytes(payload)
    updated = {
        "path": seal.PACKET_RELATIVE_PATH.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }
    monkeypatch.setitem(seal._EXPECTED_FROZEN_INPUTS, "packet", updated)
    control_path = root / seal.CONTROL_RELATIVE_PATH
    control = yaml.safe_load(control_path.read_text(encoding="utf-8"))
    control["frozen_inputs"]["packet"] = updated
    control_path.write_text(yaml.safe_dump(control, sort_keys=False), encoding="utf-8")


def test_capture_seals_exact_existing_blank_packet_without_rebuild(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    calls = _allow_fixture_git(monkeypatch)
    opened_paths: list[str] = []
    validations = 0
    original_validate = seal._validate_packet_payload

    def tracking_reader(
        project_root: Path,
        path: Path,
        label: str,
        **kwargs: object,
    ):
        del label
        opened_paths.append(path.relative_to(project_root).as_posix())
        return seal._read_stable_file(project_root, path, "tracked seal input", **kwargs)

    def count_validation(*args: object, **kwargs: object) -> None:
        nonlocal validations
        validations += 1
        original_validate(*args, **kwargs)

    monkeypatch.setattr(seal, "_validate_packet_payload", count_validation)
    packet_before = (root / seal.PACKET_RELATIVE_PATH).read_bytes()
    result = capture_e0039_review_packet_seal(root, _reader=tracking_reader)

    assert validations == 2
    assert result["state"] == seal.SEAL_STATE
    assert result["packet_capture_git_commit"] == seal.PACKET_CAPTURE_GIT_COMMIT
    assert result["seal_git_commit"] == SEAL_HEAD
    assert result["seal_git_commit"] != result["packet_capture_git_commit"]
    assert result["inventory"] == {
        "file_count": 1,
        "files": [seal.PACKET_ARTIFACT],
    }
    assert result["packet_contract"] == seal._PACKET_SUMMARY
    assert result["replay"] == {
        "packet_validation_invocation_count": 2,
        "exact_canonical_byte_equality": True,
        "canonical_encoding": "UTF8_JSON_SORTED_KEYS_COMPACT_NO_NAN_NO_DUPLICATE_KEYS_V1",
        "packet_evidence_assembly_invocation_count": 2,
        "packet_evidence_exact_canonical_byte_equality": True,
        "packet_rebuilt_or_recaptured": False,
        "clean_git_commit_equal_before_publication": True,
    }
    assert result["access_contract"] == seal._PACKET_ACCESS_RECEIPT
    assert result["authority"] == seal._AUTHORITY
    assert all(
        value is False
        for key, value in result["authority"].items()
        if key
        not in {
            "dataset_role",
            "exact_packet_hash_identity",
            "blank_predecision_contract_identity",
        }
    )

    assert opened_paths == seal._EXPECTED_OPENED_INPUT_PATHS * 2
    assert len(set(opened_paths)) == 10
    assert calls["ancestor"] == [f"{seal.PACKET_CAPTURE_GIT_COMMIT}:{SEAL_HEAD}"]
    assert set(calls["head"]) == {
        "seal control",
        "seal implementation seal_builder",
        "seal implementation capture_script",
        "packet control",
        *{f"packet implementation {name}" for name in seal._PACKET_IMPLEMENTATION_PATHS},
    }
    assert set(calls["capture"]) == {
        "packet control",
        *{f"packet implementation {name}" for name in seal._PACKET_IMPLEMENTATION_PATHS},
    }
    assert (root / seal.PACKET_RELATIVE_PATH).read_bytes() == packet_before

    output = root / seal.OUTPUT_RELATIVE_PATH
    assert output.read_bytes() == seal._encoded_seal_json(result)
    assert output.read_bytes().endswith(b"\n")
    assert len(output.read_bytes()) <= seal._RESOURCE_CAPS["maximum_seal_bytes"]


def test_sealer_opens_exact_ten_safe_paths_and_invokes_no_build_or_mapping(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    opened: list[str] = []

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("packet rebuild, capture, mapping, or decision execution is forbidden")

    monkeypatch.setattr(packet, "capture_e0039_review_packet", forbidden)
    monkeypatch.setattr(packet, "_build_unselected_rows", forbidden)
    monkeypatch.setattr(packet, "_build_alias_rows", forbidden)
    monkeypatch.setattr(
        "bctc_ai.mapping.ordered_subgraph_v2.align_ordered_subgraph_v2",
        forbidden,
    )
    monkeypatch.setattr(
        "bctc_ai.mapping.e0038_exact_search.run_e0038_exact_search",
        forbidden,
    )

    def guarding_reader(
        project_root: Path,
        path: Path,
        label: str,
        **kwargs: object,
    ):
        del label
        relative = path.relative_to(project_root).as_posix()
        lowered = relative.casefold()
        opened.append(relative)
        forbidden_fragments = (
            "reviewed_evaluation",
            "reviewed-evaluation",
            "human-review",
            "human_review",
            "e-0030",
            "e-0033",
            "e-0034",
            "postjoin",
            "numeric",
            "history",
            "mongodb",
            "duckdb",
            "qwen",
            "holdout",
            "/acb/",
            "/crops/",
            "/renders/",
        )
        assert all(fragment not in lowered for fragment in forbidden_fragments)
        return seal._read_stable_file(project_root, path, "guarded seal input", **kwargs)

    result = capture_e0039_review_packet_seal(root, _reader=guarding_reader)

    assert opened == seal._EXPECTED_OPENED_INPUT_PATHS * 2
    assert len(set(opened)) == 10
    assert result["access_contract"]["packet_evidence_inputs_reopened"] is False
    assert result["access_contract"]["prior_review_module_loaded"] is False
    assert result["access_contract"]["full_page_render_opened"] is False
    assert result["access_contract"]["packet_builder_or_capture_invocation_count"] == 0
    assert result["access_contract"]["mapping_invocation_count"] == 0


@pytest.mark.parametrize("module_name", seal._FORBIDDEN_REVIEW_MODULE_PREFIXES)
def test_preloaded_review_module_fails_before_any_input_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    root = _copy_fixture(tmp_path)
    read_called = False

    def forbidden_reader(*_args: object, **_kwargs: object):
        nonlocal read_called
        read_called = True
        raise AssertionError("contaminated process must fail before reading inputs")

    monkeypatch.setitem(sys.modules, module_name, object())
    with pytest.raises(E0039ReviewPacketSealError, match="materialized forbidden"):
        capture_e0039_review_packet_seal(root, _reader=forbidden_reader)

    assert read_called is False
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


@pytest.mark.parametrize("module_name", seal._FORBIDDEN_REVIEW_MODULE_PREFIXES)
def test_review_module_loaded_during_sealing_fails_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    module_name: str,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original_historical = seal._assert_record_matches_git_commit
    injected = False

    def contaminate(*args: object, **kwargs: object) -> None:
        nonlocal injected
        original_historical(*args, **kwargs)
        if not injected:
            injected = True
            monkeypatch.setitem(
                sys.modules,
                module_name,
                object(),
            )

    monkeypatch.setattr(seal, "_assert_record_matches_git_commit", contaminate)
    with pytest.raises(E0039ReviewPacketSealError, match="materialized forbidden"):
        capture_e0039_review_packet_seal(root)

    assert injected is True
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


def test_fresh_import_does_not_materialize_review_module() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import importlib,sys;"
                "module=importlib.import_module("
                "'bctc_ai.evaluation.e0039_review_packet_seal');"
                "assert not any(name in sys.modules for name in "
                "module._FORBIDDEN_REVIEW_MODULE_PREFIXES);"
                "assert all('e0038_reviewed_evaluation' not in p.as_posix() "
                "for p in module._FROZEN_PATHS.values())"
            ),
        ],
        cwd=REPOSITORY_ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr


def test_capture_requires_clean_git_before_any_input_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    read_called = False

    def dirty_git(_root: Path) -> str:
        raise seal.E0038ExactMappingError("dirty or untracked worktree")

    def forbidden_reader(*_args: object, **_kwargs: object):
        nonlocal read_called
        read_called = True
        raise AssertionError("input read preceded the clean-Git gate")

    monkeypatch.setattr(seal, "_clean_git_commit", dirty_git)
    with pytest.raises(E0039ReviewPacketSealError, match="dirty or untracked"):
        capture_e0039_review_packet_seal(root, _reader=forbidden_reader)

    assert read_called is False
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


def test_capture_requires_packet_capture_commit_to_be_ancestor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    read_called = False
    monkeypatch.setattr(seal, "_clean_git_commit", lambda _root: SEAL_HEAD)

    def reject_ancestor(_root: Path, _capture: str, _seal: str) -> None:
        raise E0039ReviewPacketSealError("not an ancestor")

    def forbidden_reader(*_args: object, **_kwargs: object):
        nonlocal read_called
        read_called = True
        raise AssertionError("input read preceded ancestor gate")

    monkeypatch.setattr(seal, "_assert_capture_commit_ancestor", reject_ancestor)
    with pytest.raises(E0039ReviewPacketSealError, match="not an ancestor"):
        capture_e0039_review_packet_seal(root, _reader=forbidden_reader)

    assert read_called is False
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


def test_capture_refuses_overwrite_and_symlink(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    output = root / seal.OUTPUT_RELATIVE_PATH
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("existing\n", encoding="utf-8")
    with pytest.raises(E0039ReviewPacketSealError, match="symlink|refusing to overwrite"):
        capture_e0039_review_packet_seal(root)
    assert output.read_text(encoding="utf-8") == "existing\n"

    output.unlink()
    output.symlink_to(root / "missing.json")
    with pytest.raises(E0039ReviewPacketSealError, match="symlink|refusing to overwrite"):
        capture_e0039_review_packet_seal(root)
    assert output.is_symlink()


def test_capture_rejects_noncanonical_paths(tmp_path: Path) -> None:
    root = _copy_fixture(tmp_path)
    with pytest.raises(E0039ReviewPacketSealError, match="canonical"):
        capture_e0039_review_packet_seal(
            root,
            config_path=root / seal.CONTROL_RELATIVE_PATH,
        )
    with pytest.raises(E0039ReviewPacketSealError, match="canonical"):
        capture_e0039_review_packet_seal(root, packet_path=Path("output/wrong.json"))
    with pytest.raises(E0039ReviewPacketSealError, match="canonical"):
        capture_e0039_review_packet_seal(root, output_path=Path("docs/wrong.json"))


def test_capture_fails_closed_on_final_recheck_race(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original = seal._assert_unchanged

    def fail_packet_recheck(
        reader: object,
        project_root: Path,
        stable: object,
        label: str,
    ) -> None:
        if label.endswith("packet"):
            raise seal.E0038ExactMappingError("simulated packet race")
        original(reader, project_root, stable, label)

    monkeypatch.setattr(seal, "_assert_unchanged", fail_packet_recheck)
    with pytest.raises(E0039ReviewPacketSealError, match="changed before publication"):
        capture_e0039_review_packet_seal(root)
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


def test_capture_fails_closed_on_head_or_capture_blob_mismatch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    monkeypatch.setattr(seal, "_clean_git_commit", lambda _root: SEAL_HEAD)
    monkeypatch.setattr(
        seal,
        "_assert_capture_commit_ancestor",
        lambda _root, _capture, _seal: None,
    )

    def reject_head(*_args: object, **_kwargs: object) -> None:
        raise E0039ReviewPacketSealError("simulated HEAD mismatch")

    monkeypatch.setattr(seal, "_head_bind", reject_head)
    with pytest.raises(E0039ReviewPacketSealError, match="HEAD mismatch"):
        capture_e0039_review_packet_seal(root)
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()

    root = _copy_fixture(tmp_path / "capture")
    _allow_fixture_git(monkeypatch)

    def reject_capture(*_args: object, **_kwargs: object) -> None:
        raise E0039ReviewPacketSealError("simulated capture-commit mismatch")

    monkeypatch.setattr(seal, "_assert_record_matches_git_commit", reject_capture)
    with pytest.raises(E0039ReviewPacketSealError, match="capture-commit mismatch"):
        capture_e0039_review_packet_seal(root)
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


def test_inherited_publisher_rolls_back_parent_detachment(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original_link = exact_mapping.os.link
    output_parent = root / seal.OUTPUT_RELATIVE_PATH.parent

    def racing_link(*args: object, **kwargs: object) -> None:
        original_link(*args, **kwargs)
        output_parent.rename(root / "detached-docs")
        output_parent.mkdir(parents=True)

    monkeypatch.setattr(exact_mapping.os, "link", racing_link)
    with pytest.raises(E0039ReviewPacketSealError, match="publish"):
        capture_e0039_review_packet_seal(root)

    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()
    assert not (root / "detached-docs" / seal.OUTPUT_RELATIVE_PATH.name).exists()


def test_pretty_packet_bytes_are_rejected_even_with_coordinated_record_update(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    packet_path = root / seal.PACKET_RELATIVE_PATH
    decoded = json.loads(packet_path.read_bytes())
    pretty = (
        json.dumps(decoded, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    ).encode("utf-8")
    _replace_fixture_packet(root, monkeypatch, pretty)

    with pytest.raises(E0039ReviewPacketSealError, match="canonical replay"):
        capture_e0039_review_packet_seal(root)
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


@pytest.mark.parametrize(
    "mutation",
    ["duplicate_key", "nonfinite", "truncated", "oversize", "nonblank_response"],
)
def test_malformed_or_answered_packet_is_wrapped_and_rejected_before_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    root = _copy_fixture(tmp_path)
    _allow_fixture_git(monkeypatch)
    original = (root / seal.PACKET_RELATIVE_PATH).read_bytes()
    if mutation == "duplicate_key":
        mutated = b'{"access_contract":null,' + original[1:]
    elif mutation == "nonfinite":
        mutated = original.replace(b'"format_version":1', b'"format_version":NaN', 1)
        assert mutated != original
    elif mutation == "truncated":
        mutated = original[:-1]
    elif mutation == "oversize":
        mutated = b" " * (seal._RESOURCE_CAPS["maximum_packet_bytes"] + 1)
    else:
        decoded = json.loads(original)
        decoded["blank_response_contracts"]["row_adjudication"]["template"]["decision"] = (
            "UNRESOLVED"
        )
        mutated = json.dumps(
            decoded,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    _replace_fixture_packet(root, monkeypatch, mutated)

    with pytest.raises(E0039ReviewPacketSealError):
        capture_e0039_review_packet_seal(root)
    assert not (root / seal.OUTPUT_RELATIVE_PATH).exists()


@pytest.mark.parametrize(
    "mutation",
    [
        "packet_inventory_hash",
        "packet_capture_commit",
        "seal_commit",
        "row_count",
        "blank_template",
        "access_review_loaded",
        "access_evidence_reopened",
        "authority_adjudication",
        "authority_s3",
        "replay_count",
        "seal_implementation_hash",
        "extra_field",
    ],
)
def test_seal_self_validator_rejects_coordinated_drift(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    mutation: str,
) -> None:
    _root, result = _capture_fixture(tmp_path, monkeypatch)
    drifted = copy.deepcopy(result)
    if mutation == "packet_inventory_hash":
        drifted["inventory"]["files"][0]["sha256"] = "0" * 64
    elif mutation == "packet_capture_commit":
        drifted["packet_capture_git_commit"] = "c" * 40
    elif mutation == "seal_commit":
        drifted["seal_git_commit"] = "c" * 40
    elif mutation == "row_count":
        drifted["packet_contract"]["row_count"] = 5
    elif mutation == "blank_template":
        drifted["packet_contract"]["row_response_template"]["decision"] = "UNRESOLVED"
    elif mutation == "access_review_loaded":
        drifted["access_contract"]["prior_review_module_loaded"] = True
    elif mutation == "access_evidence_reopened":
        drifted["access_contract"]["packet_evidence_inputs_reopened"] = True
    elif mutation == "authority_adjudication":
        drifted["authority"]["row_adjudication_completed"] = True
    elif mutation == "authority_s3":
        drifted["authority"]["s3_durability_registration"] = True
    elif mutation == "replay_count":
        drifted["replay"]["packet_validation_invocation_count"] = 1
    elif mutation == "seal_implementation_hash":
        drifted["input_hash_ledger"]["seal_implementation"]["seal_builder"]["sha256"] = "0" * 64
    elif mutation == "extra_field":
        drifted["recommended_answer"] = 4311

    with pytest.raises(E0039ReviewPacketSealError):
        seal._validate_seal_payload(drifted, **_validation_arguments(result))


def test_control_pins_exact_ten_paths_and_all_implementations() -> None:
    control = yaml.safe_load((REPOSITORY_ROOT / seal.CONTROL_RELATIVE_PATH).read_text())

    assert control["frozen_inputs"] == seal._EXPECTED_FROZEN_INPUTS
    assert set(control["frozen_inputs"]) == set(seal._FROZEN_PATHS)
    assert control["access_contract"] == seal._ACCESS_CONTROL
    assert control["seal_contract"] == seal._SEAL_CONTRACT
    assert control["resource_caps"] == seal._RESOURCE_CAPS
    assert control["publication"] == seal._PUBLICATION_CONTRACT
    assert control["claim_boundary"] == seal._CLAIM_BOUNDARY
    assert len(seal._EXPECTED_OPENED_INPUT_PATHS) == 10
    assert len(set(seal._EXPECTED_OPENED_INPUT_PATHS)) == 10
    assert all(
        "e0038_reviewed_evaluation" not in path for path in seal._EXPECTED_OPENED_INPUT_PATHS
    )
    for name, relative in seal._IMPLEMENTATION_PATHS.items():
        payload = (REPOSITORY_ROOT / relative).read_bytes()
        assert control["implementation"][name] == {
            "path": relative.as_posix(),
            "sha256": hashlib.sha256(payload).hexdigest(),
            "size_bytes": len(payload),
        }
    assert control["output"] == {"path": seal.OUTPUT_RELATIVE_PATH.as_posix()}


def test_captured_packet_is_immutable_and_formal_seal_is_absent() -> None:
    packet_bytes = (REPOSITORY_ROOT / seal.PACKET_RELATIVE_PATH).read_bytes()
    assert hashlib.sha256(packet_bytes).hexdigest() == seal.PACKET_ARTIFACT["sha256"]
    assert len(packet_bytes) == seal.PACKET_ARTIFACT["size_bytes"]
    assert not (REPOSITORY_ROOT / seal.OUTPUT_RELATIVE_PATH).exists()


def test_real_capture_commit_ancestry_and_historical_packet_blobs() -> None:
    current = subprocess.run(
        ["git", "-C", str(REPOSITORY_ROOT), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    seal._assert_capture_commit_ancestor(
        REPOSITORY_ROOT,
        seal.PACKET_CAPTURE_GIT_COMMIT,
        current,
    )
    seal._assert_record_matches_git_commit(
        REPOSITORY_ROOT,
        seal.PACKET_CONTROL_ARTIFACT,
        name="packet control",
        expected_path=seal.PACKET_CONTROL_RELATIVE_PATH,
        commit=seal.PACKET_CAPTURE_GIT_COMMIT,
    )
    for packet_name, path in seal._PACKET_IMPLEMENTATION_PATHS.items():
        input_name = seal._PACKET_INPUT_NAME_BY_IMPLEMENTATION[packet_name]
        seal._assert_record_matches_git_commit(
            REPOSITORY_ROOT,
            seal._EXPECTED_FROZEN_INPUTS[input_name],
            name=packet_name,
            expected_path=path,
            commit=seal.PACKET_CAPTURE_GIT_COMMIT,
        )
