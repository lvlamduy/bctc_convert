from __future__ import annotations

import importlib.util
import inspect
import json
import os
import stat
import sys
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version as distribution_version
from pathlib import Path

import fitz
import pytest

from bctc_ai.corpus import wave1_role_b_full_reader_v2 as full
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WaveOneRoleBWordBoxNormalizationError,
    normalize_ppocrv6_word_boxes,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
PLAN_PATH = (
    PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
    "wave-1-role-b-page-read-plan.json"
)
_WORKER_SPEC = importlib.util.spec_from_file_location(
    "run_ppocrv6_wave1_full_worker_v2_for_test",
    PROJECT_ROOT / "scripts/models/run_ppocrv6_wave1_full_worker_v2.py",
)
assert _WORKER_SPEC is not None and _WORKER_SPEC.loader is not None
full_worker = importlib.util.module_from_spec(_WORKER_SPEC)
sys.modules[_WORKER_SPEC.name] = full_worker
_WORKER_SPEC.loader.exec_module(full_worker)


def _sealed_plan() -> dict:
    return json.loads(PLAN_PATH.read_bytes())


def _minimal_request(request_sha: str, *, route: str, ordinal: int, document_id: str) -> dict:
    return {
        "request_ordinal": ordinal,
        "document_id": document_id,
        "source_sha256": document_id.removeprefix("sha256:"),
        "source_size_bytes": 1,
        "physical_page": ordinal,
        "route": route,
        "request_sha256": request_sha,
        "request": {"route": route},
    }


def _response_names(request_sha: str, nonce: str = "b" * 32) -> tuple[str, str]:
    final = f"{request_sha}.response.json"
    return final, f".{final}.{nonce}.tmp"


def _open_directory(path: Path) -> int:
    return os.open(
        path,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
    )


class _FakeProcess:
    def __init__(self, codes: list[int | None], on_poll=None) -> None:
        self._codes = list(codes)
        self._on_poll = on_poll

    def poll(self) -> int | None:
        if self._on_poll is not None:
            callback, self._on_poll = self._on_poll, None
            callback()
        if len(self._codes) > 1:
            return self._codes.pop(0)
        return self._codes[0]


def test_worker_response_publication_four_phases_are_closed_and_nonmutating(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    final, temporary = _response_names("a" * 64)
    allowed = frozenset({final})
    payload = b'{"response":"exact"}\n'
    descriptor = _open_directory(directory)
    try:
        assert full._read_worker_response_publication(
            descriptor, final, allowed_filenames=allowed
        ) == (full._WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None)
        (directory / temporary).write_bytes(payload)
        (directory / temporary).chmod(0o600)
        assert full._read_worker_response_publication(
            descriptor, final, allowed_filenames=allowed
        ) == (full._WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None)
        (directory / temporary).chmod(0o444)
        assert full._read_worker_response_publication(
            descriptor, final, allowed_filenames=allowed
        ) == (full._WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None)
        os.link(temporary, final, src_dir_fd=descriptor, dst_dir_fd=descriptor)
        pair_before = (
            os.stat(final, dir_fd=descriptor, follow_symlinks=False),
            os.stat(temporary, dir_fd=descriptor, follow_symlinks=False),
        )
        assert full._read_worker_response_publication(
            descriptor, final, allowed_filenames=allowed
        ) == (full._WORKER_RESPONSE_PUBLICATION_IN_PROGRESS, None)
        pair_after = (
            os.stat(final, dir_fd=descriptor, follow_symlinks=False),
            os.stat(temporary, dir_fd=descriptor, follow_symlinks=False),
        )
        assert [(item.st_dev, item.st_ino, item.st_nlink) for item in pair_after] == [
            (item.st_dev, item.st_ino, item.st_nlink) for item in pair_before
        ]
        os.unlink(temporary, dir_fd=descriptor)
        assert full._read_worker_response_publication(
            descriptor, final, allowed_filenames=allowed
        ) == (full._WORKER_RESPONSE_READY, payload)
    finally:
        os.close(descriptor)


def test_ready_current_response_allows_one_well_formed_future_prelink_temp(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    first, _first_temporary = _response_names("a" * 64)
    second, second_temporary = _response_names("b" * 64, "c" * 32)
    payload = b"first\n"
    (directory / first).write_bytes(payload)
    (directory / first).chmod(0o444)
    (directory / second_temporary).write_bytes(b"partial")
    (directory / second_temporary).chmod(0o600)
    descriptor = _open_directory(directory)
    try:
        assert full._read_worker_response_publication(
            descriptor,
            first,
            allowed_filenames=frozenset({first, second}),
        ) == (full._WORKER_RESPONSE_READY, payload)
    finally:
        os.close(descriptor)


def test_cleanup_between_pair_observations_freshly_reclassifies_ready(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    final, temporary = _response_names("a" * 64)
    payload = b"exact\n"
    (directory / temporary).write_bytes(payload)
    (directory / temporary).chmod(0o444)
    descriptor = _open_directory(directory)
    os.link(temporary, final, src_dir_fd=descriptor, dst_dir_fd=descriptor)
    original = full._nofollow_response_stat
    removed = False

    def unlink_after_final_stat(directory_fd: int, name: str):
        nonlocal removed
        identity = original(directory_fd, name)
        if name == final and identity is not None and identity.st_nlink == 2 and not removed:
            os.unlink(temporary, dir_fd=directory_fd)
            removed = True
        return identity

    monkeypatch.setattr(full, "_nofollow_response_stat", unlink_after_final_stat)
    try:
        assert full._read_worker_response_publication(descriptor, final) == (
            full._WORKER_RESPONSE_READY,
            payload,
        )
    finally:
        os.close(descriptor)


def test_link_between_directory_list_and_final_stat_reclassifies_pending(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    final, temporary = _response_names("a" * 64)
    (directory / temporary).write_bytes(b"exact\n")
    (directory / temporary).chmod(0o444)
    descriptor = _open_directory(directory)
    original = full._worker_response_temporaries
    linked = False

    def link_after_list(directory_fd: int, filename: str, allowed: frozenset[str]):
        nonlocal linked
        result = original(directory_fd, filename, allowed)
        if not linked:
            os.link(temporary, final, src_dir_fd=directory_fd, dst_dir_fd=directory_fd)
            linked = True
        return result

    monkeypatch.setattr(full, "_worker_response_temporaries", link_after_list)
    try:
        assert full._read_worker_response_publication(descriptor, final) == (
            full._WORKER_RESPONSE_PUBLICATION_IN_PROGRESS,
            None,
        )
    finally:
        os.close(descriptor)


def test_ready_response_replacement_between_stat_and_open_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    final, _temporary = _response_names("a" * 64)
    (directory / final).write_bytes(b"original\n")
    (directory / final).chmod(0o444)
    descriptor = _open_directory(directory)
    original = full._read_response_bytes_at
    swapped = False

    def swap_before_read(directory_fd: int, name: str, *, cleanup_transition_allowed: bool):
        nonlocal swapped
        if name == final and not swapped:
            os.unlink(final, dir_fd=directory_fd)
            replacement = os.open(
                final,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
                dir_fd=directory_fd,
            )
            os.write(replacement, b"replacement\n")
            os.fchmod(replacement, 0o444)
            os.close(replacement)
            swapped = True
        return original(
            directory_fd,
            name,
            cleanup_transition_allowed=cleanup_transition_allowed,
        )

    monkeypatch.setattr(full, "_read_response_bytes_at", swap_before_read)
    try:
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="identity drifted"):
            full._read_worker_response_publication(descriptor, final)
    finally:
        os.close(descriptor)


def test_response_publication_foreign_temp_wrong_pair_nlink3_mode_and_symlink_abort(
    tmp_path: Path,
) -> None:
    for case in ("foreign", "wrong_pair", "nlink3", "mode", "symlink"):
        directory = tmp_path / case
        directory.mkdir()
        final, temporary = _response_names("a" * 64)
        second, _second_temporary = _response_names("b" * 64)
        allowed = frozenset({final, second})
        if case == "foreign":
            (directory / f".{final}.not-hex.tmp").write_bytes(b"x")
        elif case == "wrong_pair":
            (directory / final).write_bytes(b"one")
            (directory / final).chmod(0o444)
            os.link(directory / final, directory / second)
            (directory / temporary).write_bytes(b"two")
            (directory / temporary).chmod(0o444)
        elif case == "nlink3":
            (directory / temporary).write_bytes(b"one")
            (directory / temporary).chmod(0o444)
            os.link(directory / temporary, directory / final)
            os.link(directory / temporary, directory / second)
        elif case == "mode":
            (directory / final).write_bytes(b"one")
            (directory / final).chmod(0o600)
        else:
            target = tmp_path / "symlink-target"
            if not target.exists():
                target.write_bytes(b"one")
            (directory / final).symlink_to(target)
        descriptor = _open_directory(directory)
        try:
            with pytest.raises(full.WaveOneRoleBFullReaderError):
                full._read_worker_response_publication(descriptor, final, allowed_filenames=allowed)
        finally:
            os.close(descriptor)


def test_paused_link_cleanup_zero_exit_is_ready_but_nonzero_never_consumes(
    tmp_path: Path,
) -> None:
    directory = tmp_path / "responses"
    directory.mkdir()
    final, temporary = _response_names("a" * 64)
    payload = b"exact\n"
    (directory / temporary).write_bytes(payload)
    (directory / temporary).chmod(0o444)
    descriptor = _open_directory(directory)
    os.link(temporary, final, src_dir_fd=descriptor, dst_dir_fd=descriptor)
    try:
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="failed: 9"):
            full._poll_worker_response_publication(
                _FakeProcess([9]), descriptor, final, allowed_filenames=frozenset({final})
            )
        assert os.stat(final, dir_fd=descriptor, follow_symlinks=False).st_nlink == 2

        def cleanup() -> None:
            os.unlink(temporary, dir_fd=descriptor)

        assert full._poll_worker_response_publication(
            _FakeProcess([0], on_poll=cleanup),
            descriptor,
            final,
            allowed_filenames=frozenset({final}),
        ) == (full._WORKER_RESPONSE_READY, payload, 0)
    finally:
        os.close(descriptor)


def test_v2_policy_control_runtime_and_ledger_are_isolated_from_v1(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = full._load_policy(PROJECT_ROOT)
    assert policy["version"] == 2
    assert policy["policy"] == "BANK_CORPUS_WAVE_1_ROLE_B_FULL_PAGE_READER_V2"
    assert policy["output"]["root"].endswith("/full-v2")
    assert policy["worker"]["script"].endswith("_full_worker_v2.py")
    assert (
        policy["worker"]["protocol"]
        == "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_WITH_PUBLICATION_STATE_V2"
    )
    paths = {path.as_posix() for path in full.FULL_READER_IMPLEMENTATION_RELATIVE_PATHS}
    assert {
        "config/corpus/bank-corpus-wave-1-role-b-full-reader-v2.yaml",
        "src/bctc_ai/corpus/wave1_role_b_full_reader_v2.py",
        "scripts/models/run_ppocrv6_wave1_full_worker_v2.py",
        "scripts/corpus/run_wave1_role_b_full_reader_v2.py",
    } <= paths
    assert {
        "config/corpus/bank-corpus-wave-1-role-b-full-reader-v1.yaml",
        "src/bctc_ai/corpus/wave1_role_b_full_reader.py",
        "scripts/models/run_ppocrv6_wave1_full_worker.py",
        "scripts/corpus/run_wave1_role_b_full_reader.py",
    }.isdisjoint(paths)
    executor = {
        "git": {"commit": "a" * 40, "dirty": False},
        "implementation_ledger": {"records": [], "sha256": "e" * 64},
    }
    monkeypatch.setattr(
        full,
        "_authenticate_plan",
        lambda *_args, **_kwargs: (_sealed_plan(), policy, executor),
    )
    control = full.build_authenticated_control(PROJECT_ROOT, model_cache=PROJECT_ROOT)
    assert control["format_version"] == "BANK_CORPUS_WAVE_1_ROLE_B_FULL_READER_CONTROL_V2"
    assert control["worker_contract"]["protocol"] == policy["worker"]["protocol"]
    assert control["executor_implementation_ledger"] == executor["implementation_ledger"]


def test_cross_control_v1_checkpoint_cannot_be_adopted_under_full_v2(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full-v2"))
    document_id = "sha256:" + "a" * 64
    request_sha = "b" * 64
    page = _minimal_request(
        request_sha,
        route=full._OCR_ROUTE,
        ordinal=1,
        document_id=document_id,
    )
    new_control = {
        "control_identity_sha256": "f" * 64,
        "sentinel_request_sha256s": [],
        "documents": [{"document_id": document_id, "pages": [page]}],
    }
    old_control = deepcopy(new_control)
    old_control["control_identity_sha256"] = "e" * 64
    record = {"request_sha256": request_sha}
    checkpoint = full._checkpoint_payload(old_control, document_id, record, 1, None)
    payload = full._canonical_bytes(checkpoint)
    digest = full.sha256_bytes(payload)
    directory = tmp_path / "full-v2/checkpoints" / ("a" * 64)
    directory.mkdir(parents=True)
    path = directory / f"0001-{digest}.json"
    path.write_bytes(payload)
    path.chmod(0o444)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="checkpoint chain drifted"):
        full._load_document_checkpoints(tmp_path, new_control, document_id)


def test_v2_runtime_has_no_failed_v1_archive_locator() -> None:
    for path in (
        full.POLICY_RELATIVE_PATH,
        Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v2.py"),
        Path("scripts/models/run_ppocrv6_wave1_full_worker_v2.py"),
        Path("scripts/corpus/run_wave1_role_b_full_reader_v2.py"),
    ):
        text = (PROJECT_ROOT / path).read_text(encoding="utf-8")
        assert "full-v1-failed" not in text
        assert "full-v1/" not in text
    active_reader = inspect.getsource(full._run_ocr_batches) + inspect.getsource(
        full._read_worker_response_publication
    )
    assert "_recover_owned_hardlink_temporaries" not in active_reader


def _run_synthetic_ocr_batch(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    request_count: int,
    publication: str,
    appended_sink: list[str] | None = None,
    state_sink: dict | None = None,
) -> tuple[dict, list[str]]:
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full-v2"))
    monkeypatch.setattr(full, "_ensure_capacity", lambda *_args: None)
    monkeypatch.setattr(full, "_worker_environment", lambda *_args: {})
    monkeypatch.setattr(full, "_materialize_private_inputs", lambda *_args: {})
    monkeypatch.setattr(full, "_build_worker_task", lambda *_args: {"task": "synthetic"})
    monkeypatch.setattr(full, "_append_timing", lambda *_args: None)
    monkeypatch.setattr(full.secrets, "token_hex", lambda _size: "d" * 64)
    interpreter = tmp_path / "interpreter"
    worker = tmp_path / "worker.py"
    interpreter.write_bytes(b"interpreter")
    worker.write_bytes(b"worker")
    monkeypatch.setattr(full, "_project_path", lambda root, relative, _label: root / relative)
    appended = appended_sink if appended_sink is not None else []

    def append_checkpoint(
        _root: Path,
        _control: dict,
        records_by_document: dict[str, list[dict]],
        _heads_by_document: dict[str, str | None],
        record: dict,
    ) -> None:
        assert record["request_sha256"] not in appended
        appended.append(record["request_sha256"])
        records_by_document[record["document_id"]].append(record)

    monkeypatch.setattr(full, "_append_checkpoint", append_checkpoint)
    monkeypatch.setattr(
        full,
        "_consume_worker_response",
        lambda _root, _control, expected, _render, _payload, **_kwargs: (
            {
                "request_sha256": expected["request_sha256"],
                "document_id": expected["document_id"],
            },
            {"inference_wall_seconds": 0.0, "model_load_wall_seconds": 0.0},
        ),
    )
    document_id = "sha256:" + "a" * 64
    requests = [
        {
            "request_ordinal": index + 1,
            "request_sha256": f"{index + 1:064x}",
            "document_id": document_id,
        }
        for index in range(request_count)
    ]
    renders = {request["request_sha256"]: {"ref": {"sha256": "f" * 64}} for request in requests}

    class SyntheticPopen:
        def __init__(self, command, **_kwargs) -> None:
            response_directory = Path(command[command.index("--response-directory") + 1])
            self._response_directory = response_directory
            self._poll_count = 0
            for request in requests:
                final, temporary = _response_names(request["request_sha256"])
                if publication.startswith("pair"):
                    if request is not requests[0]:
                        continue
                    (response_directory / temporary).write_bytes(b"response\n")
                    (response_directory / temporary).chmod(0o444)
                    os.link(response_directory / temporary, response_directory / final)
                else:
                    (response_directory / final).write_bytes(b"response\n")
                    (response_directory / final).chmod(0o444)

        def poll(self) -> int | None:
            self._poll_count += 1
            if publication == "ready_then_nonzero":
                return None if self._poll_count == 1 else 9
            if publication == "pair_nonzero":
                return 9
            if publication == "pair_cleanup_after_none":
                if self._poll_count == 1:
                    return None
                final, temporary = _response_names(requests[0]["request_sha256"])
                del final
                path = self._response_directory / temporary
                if path.exists():
                    path.unlink()
                return 0
            return 0

        def terminate(self) -> None:
            pytest.fail("a completed synthetic worker must not be terminated")

        def kill(self) -> None:
            pytest.fail("a completed synthetic worker must not be killed")

        def wait(self, timeout=None) -> int:
            del timeout
            return self.poll() or 0

    monkeypatch.setattr(full.subprocess, "Popen", SyntheticPopen)
    control = {"sharding": {"shards": [{"shard_id": 0, "requests": requests}]}}
    policy = {
        "execution": {"minimum_free_space_bytes": 0},
        "worker": {
            "interpreter": "interpreter",
            "script": "worker.py",
            "max_no_progress_seconds": 2,
            "worker_shutdown_grace_seconds": 1,
        },
    }
    records_by_document = {document_id: []}
    heads_by_document = {document_id: None}
    if state_sink is not None:
        state_sink["records"] = records_by_document
        state_sink["heads"] = heads_by_document
    result = full._run_ocr_batches(
        tmp_path,
        tmp_path,
        {},
        policy,
        control,
        renders,
        records_by_document,
        heads_by_document,
        -1,
    )
    return result, appended


def test_exited_zero_worker_drains_multiple_ready_responses_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, appended = _run_synthetic_ocr_batch(
        tmp_path, monkeypatch, request_count=3, publication="ready"
    )
    assert result["inference_request_count"] == 3
    assert appended == [f"{index:064x}" for index in (1, 2, 3)]


def test_full_loop_pair_pending_cleanup_after_none_checkpoints_exactly_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    result, appended = _run_synthetic_ocr_batch(
        tmp_path,
        monkeypatch,
        request_count=1,
        publication="pair_cleanup_after_none",
    )
    assert result["status"] == "COMPLETE_PINNED_PPOCRV6_BATCHES_CHECKPOINTED"
    assert appended == [f"{1:064x}"]


def test_full_loop_nonzero_worker_with_pending_pair_writes_no_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    appended: list[str] = []
    state: dict = {}
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="failed: 9"):
        _run_synthetic_ocr_batch(
            tmp_path,
            monkeypatch,
            request_count=1,
            publication="pair_nonzero",
            appended_sink=appended,
            state_sink=state,
        )
    assert appended == []
    assert next(iter(state["records"].values())) == []
    assert next(iter(state["heads"].values())) is None
    assert not (tmp_path / "full-v2/checkpoints").exists()


def test_full_loop_does_not_ignore_nonzero_exit_after_last_ready_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="failed: 9"):
        _run_synthetic_ocr_batch(
            tmp_path, monkeypatch, request_count=1, publication="ready_then_nonzero"
        )


def test_policy_is_byte_locked_and_all_routes_are_exact() -> None:
    policy = full._load_policy(PROJECT_ROOT)
    assert policy["expected"] == {
        "document_count": 27,
        "request_count": 1449,
        "ocr_request_count": 1356,
        "native_request_count": 93,
        "sentinel_adopted_ocr_request_count": 24,
        "remaining_ocr_request_count": 1332,
        "shard_count": 2,
        "remaining_ocr_requests_per_shard": [665, 667],
        "remaining_ocr_documents_per_shard": [13, 13],
        "statement_classification_count": 0,
        "table_classification_count": 0,
        "row_reconstruction_count": 0,
        "cell_interpretation_count": 0,
        "absence_declaration_count": 0,
    }
    records = full._full_request_records(_sealed_plan())
    assert len(records) == 1449
    assert sum(record["route"] == full._OCR_ROUTE for record in records) == 1356
    assert sum(record["route"] == full._NATIVE_ROUTE for record in records) == 93
    assert all("bank" not in record and "relative_path" not in record for record in records)


def test_whole_document_lpt_is_deterministic_and_exact() -> None:
    sealed = _sealed_plan()
    records = full._full_request_records(sealed)
    sentinel_hashes = set(full._sentinel_request_hashes(sealed))
    first = full._assign_remaining_ocr_shards(records, sentinel_hashes)
    second = full._assign_remaining_ocr_shards(deepcopy(records), set(sentinel_hashes))
    assert full._canonical_bytes(first) == full._canonical_bytes(second)
    assert [shard["request_count"] for shard in first] == [665, 667]
    assert [shard["document_count"] for shard in first] == [13, 13]
    assert set(first[0]["document_ids"]).isdisjoint(first[1]["document_ids"])
    assert sum(len(shard["requests"]) for shard in first) == 1332


def test_completion_order_is_staged_and_checkpoint_is_one_page_delta() -> None:
    document_id = "sha256:" + "a" * 64
    sentinel_sha = "1" * 64
    ocr_sha = "2" * 64
    native_sha = "3" * 64
    pages = [
        _minimal_request(ocr_sha, route=full._OCR_ROUTE, ordinal=1, document_id=document_id),
        _minimal_request(sentinel_sha, route=full._OCR_ROUTE, ordinal=2, document_id=document_id),
        _minimal_request(native_sha, route=full._NATIVE_ROUTE, ordinal=3, document_id=document_id),
    ]
    control = {
        "control_identity_sha256": "f" * 64,
        "sentinel_request_sha256s": [sentinel_sha],
        "documents": [{"document_id": document_id, "pages": pages}],
    }
    assert full._document_completion_order(control, document_id) == [
        sentinel_sha,
        ocr_sha,
        native_sha,
    ]
    record = {"request_sha256": sentinel_sha, "payload": "x"}
    first = full._checkpoint_payload(control, document_id, record, 1, None)
    second = full._checkpoint_payload(control, document_id, record, 2, "e" * 64)
    assert first["page_record"] == record
    assert second["page_record"] == record
    assert "completed" not in first and "completed" not in second
    assert len(full._canonical_bytes(second)) - len(full._canonical_bytes(first)) < 80


def test_checkpoint_resume_quarantines_exact_interrupted_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output = Path("evidence/full-v2")
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", output)
    document_id = "sha256:" + "a" * 64
    checkpoint_dir = tmp_path / output / "checkpoints" / ("a" * 64)
    checkpoint_dir.mkdir(parents=True)
    temporary = checkpoint_dir / ("." + "0001-" + "b" * 64 + ".json." + "c" * 32 + ".tmp")
    temporary.write_bytes(b"partial")
    temporary.chmod(0o600)
    control = {
        "control_identity_sha256": "f" * 64,
        "sentinel_request_sha256s": [],
        "documents": [
            {
                "document_id": document_id,
                "pages": [
                    _minimal_request(
                        "1" * 64,
                        route=full._OCR_ROUTE,
                        ordinal=1,
                        document_id=document_id,
                    )
                ],
            }
        ],
    }
    before = (temporary.read_bytes(), temporary.stat().st_mtime_ns)
    assert full._load_document_checkpoints(
        tmp_path, control, document_id, recover_temporaries=False
    ) == ([], None)
    assert (temporary.read_bytes(), temporary.stat().st_mtime_ns) == before
    assert temporary.exists()


def test_orphan_scan_ignores_owned_standalone_publication_temporary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    request_sha = "1" * 64
    expected = {"request_sha256": request_sha}
    monkeypatch.setattr(full, "_control_index", lambda _control: {request_sha: expected})
    directory = tmp_path / "full/objects/sha256/aa"
    directory.mkdir(parents=True)
    temporary = directory / ("." + "a" * 64 + ".json." + "b" * 32 + ".tmp")
    temporary.write_bytes(b"interrupted")
    temporary.chmod(0o600)
    assert full._scan_result_orphans(tmp_path, {"sentinel_request_sha256s": []}, set()) == []
    assert temporary.exists()


def test_execution_lease_rejects_path_replacement_during_blocking_acquire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    lease_path = tmp_path / "full/locks/full-reader-execution.lease"
    original_flock = full.fcntl.flock
    replaced = False

    def replace_after_acquire(descriptor: int, operation: int) -> None:
        nonlocal replaced
        original_flock(descriptor, operation)
        if operation == full.fcntl.LOCK_EX and not replaced:
            replaced = True
            lease_path.unlink()
            replacement = os.open(lease_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(replacement)

    monkeypatch.setattr(full.fcntl, "flock", replace_after_acquire)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="while acquiring"):
        with full._execution_lease(tmp_path):
            pytest.fail("a replaced execution lease must never be yielded")


def test_document_lock_rejects_path_replacement_during_blocking_acquire(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    source_sha = "a" * 64
    lock_path = tmp_path / "full/locks/documents" / f"{source_sha}.lock"
    original_flock = full.fcntl.flock
    replaced = False

    def replace_after_acquire(descriptor: int, operation: int) -> None:
        nonlocal replaced
        original_flock(descriptor, operation)
        if operation == full.fcntl.LOCK_EX and not replaced:
            replaced = True
            lock_path.unlink()
            replacement = os.open(lock_path, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o600)
            os.close(replacement)

    monkeypatch.setattr(full.fcntl, "flock", replace_after_acquire)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="while acquiring"):
        with full._document_locks(tmp_path, [f"sha256:{source_sha}"]):
            pytest.fail("a replaced document lock must never be yielded")


def test_sentinel_object_adoption_is_a_byte_copy_not_a_hardlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full, "SENTINEL_RELATIVE_ROOT", Path("sentinel"))
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    payload = b"immutable evidence\n"
    digest = full.sha256_bytes(payload)
    reference = {
        "path": f"objects/sha256/{digest[:2]}/{digest}.json",
        "sha256": digest,
        "size_bytes": len(payload),
    }
    source = full._publish_exclusive(
        tmp_path,
        Path("sentinel/objects/sha256") / digest[:2],
        f"{digest}.json",
        payload,
    )
    source_before = source.stat(follow_symlinks=False)
    assert full._copy_sentinel_object(tmp_path, reference, ".json") == reference
    destination = tmp_path / "full" / reference["path"]
    source_after = source.stat(follow_symlinks=False)
    destination_stat = destination.stat(follow_symlinks=False)
    assert source.read_bytes() == destination.read_bytes() == payload
    assert (
        source_before.st_ino,
        source_before.st_mtime_ns,
        stat.S_IMODE(source_before.st_mode),
    ) == (
        source_after.st_ino,
        source_after.st_mtime_ns,
        stat.S_IMODE(source_after.st_mode),
    )
    assert (source_after.st_dev, source_after.st_ino) != (
        destination_stat.st_dev,
        destination_stat.st_ino,
    )
    assert source_after.st_nlink == destination_stat.st_nlink == 1


def test_only_word_geometry_failure_can_be_terminal_unresolved() -> None:
    sentinel_aggregate = json.loads(
        (
            PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/"
            "sentinel-v1/sentinel-aggregate.json"
        ).read_bytes()
    )
    result_ref = sentinel_aggregate["results"][0]["result_ref"]
    result = json.loads(
        (
            PROJECT_ROOT
            / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1"
            / result_ref["path"]
        ).read_bytes()
    )
    backend = json.loads(
        (
            PROJECT_ROOT
            / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1"
            / result["backend_payload_ref"]["path"]
        ).read_bytes()
    )
    raw = deepcopy(backend["raw_provider_payload"])
    width, height = result["coordinate_authority"]["pixel_dimensions"]
    raw["text_word_boxes"][0][0][2] = width + 2
    full._validate_ppocrv6_schema_except_word_geometry(raw, pixel_width=width, pixel_height=height)
    authority = {
        "policy": full.WORD_BOX_NORMALIZATION_POLICY,
        "policy_sha256": full.normalization_policy_sha256(full.WORD_BOX_NORMALIZATION_POLICY),
        "control_identity_sha256": "1" * 64,
        "normalization_producer_implementation_ledger_sha256": "2" * 64,
    }
    with pytest.raises(WaveOneRoleBWordBoxNormalizationError):
        normalize_ppocrv6_word_boxes(
            raw, pixel_width=width, pixel_height=height, authority=authority
        )
    malformed = deepcopy(raw)
    malformed["rec_scores"][0] = True
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full._validate_ppocrv6_schema_except_word_geometry(
            malformed, pixel_width=width, pixel_height=height
        )


def test_ocr_coordinate_authority_replay_and_unresolved_projection_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    sentinel_root = Path("output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1")
    sentinel_aggregate = json.loads(
        (PROJECT_ROOT / sentinel_root / "sentinel-aggregate.json").read_bytes()
    )
    source_record = sentinel_aggregate["results"][0]
    expected = {
        record["request_sha256"]: record for record in full._full_request_records(_sealed_plan())
    }[source_record["request_sha256"]]
    result = json.loads(
        (PROJECT_ROOT / sentinel_root / source_record["result_ref"]["path"]).read_bytes()
    )
    backend = json.loads(
        (PROJECT_ROOT / sentinel_root / source_record["backend_payload_ref"]["path"]).read_bytes()
    )

    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", sentinel_root)
    adopted = full._page_record(
        expected,
        status=source_record["status"],
        origin="AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
        render_ref=source_record["render_ref"],
        backend_payload_ref=source_record["backend_payload_ref"],
        result_ref=source_record["result_ref"],
        line_count=source_record["line_count"],
        word_token_count=source_record["word_token_count"],
        unresolved=False,
        word_box_correction_count=source_record["word_box_correction_count"],
        word_box_corrected_edge_count=source_record["word_box_corrected_edge_count"],
    )
    full._validate_ocr_result(PROJECT_ROOT, {}, adopted, expected)
    restored = full._restore_in_memory_coordinate_authority(result["coordinate_authority"])
    assert full.public_coordinate_authority(restored) == result["coordinate_authority"]

    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    render_ref = full._put_object(tmp_path, b"synthetic-png", suffix=".png")
    width, height = result["coordinate_authority"]["pixel_dimensions"]
    raw = deepcopy(backend["raw_provider_payload"])
    raw["text_word_boxes"][0][0][2] = width + 2
    implementation_sha = "2" * 64
    control = {
        "control_identity_sha256": "1" * 64,
        "executor_implementation_ledger": {"sha256": implementation_sha},
        "word_box_normalization": {
            "policy": full.WORD_BOX_NORMALIZATION_POLICY,
            "policy_sha256": full.normalization_policy_sha256(full.WORD_BOX_NORMALIZATION_POLICY),
            "normalization_producer_implementation_ledger_sha256": implementation_sha,
        },
    }
    render = {
        "ref": render_ref,
        "pixel_width": width,
        "pixel_height": height,
        "coordinate_authority": restored,
    }
    unresolved = full._unresolved_ocr_geometry_record(tmp_path, control, expected, render, raw)
    full._validate_page_record(tmp_path, control, unresolved, expected)
    unresolved_result = json.loads(full._read_object(tmp_path, unresolved["result_ref"], ".json"))
    assert unresolved_result["coordinate_authority"] == result["coordinate_authority"]
    assert not any(key.startswith("_") for key in unresolved_result["coordinate_authority"])
    control["sentinel_request_sha256s"] = []
    monkeypatch.setattr(
        full,
        "_control_index",
        lambda _control: {expected["request_sha256"]: expected},
    )
    adopted_orphans = full._scan_result_orphans(tmp_path, control, set())
    assert adopted_orphans == [unresolved]
    assert adopted_orphans[0]["word_box_correction_count"] == 0
    assert adopted_orphans[0]["word_box_corrected_edge_count"] == 0


def test_production_apis_have_no_provider_or_authentication_injection() -> None:
    for function in (
        full.build_authenticated_control,
        full.publish_authenticated_control,
        full.run_authenticated_full_reader,
        full.verify_authenticated_full_reader,
        full.finalize_authenticated_full_reader,
    ):
        assert list(inspect.signature(function).parameters) == ["project_root", "model_cache"]


def test_implementation_ledger_covers_dynamic_native_and_worker_dependencies() -> None:
    paths = {path.as_posix() for path in full.FULL_READER_IMPLEMENTATION_RELATIVE_PATHS}
    assert {
        "src/bctc_ai/ocr/causal_native_text_evidence_v1.py",
        "src/bctc_ai/ocr/causal_native_text.py",
        "src/bctc_ai/ocr/_causal_visibility_core.py",
        "src/bctc_ai/ocr/native_text_quality_v2.py",
        "src/bctc_ai/ocr/pdf_text.py",
        "src/bctc_ai/core/contracts.py",
        "src/bctc_ai/core/text.py",
        "scripts/models/run_ppocrv6_wave1_full_worker_v2.py",
        "scripts/models/run_ppocrv6_sentinel_worker.py",
        "src/bctc_ai/ocr/ppocrv6_page_session.py",
        "src/bctc_ai/corpus/wave1_role_b_word_box_normalization.py",
    } <= paths


def _worker_task(tmp_path: Path, count: int) -> tuple[Path, dict]:
    nonce = "a" * 64
    shard_root = tmp_path / f"execution-{nonce}" / "shard-0"
    (shard_root / "inputs").mkdir(parents=True)
    (shard_root / "responses").mkdir()
    requests = []
    for index in range(count):
        request_sha = f"{index + 1:064x}"
        requests.append(
            {
                "request_sha256": request_sha,
                "render_sha256": "b" * 64,
                "render_size_bytes": 1,
                "image_path": (shard_root / "inputs" / f"{request_sha}.png").as_posix(),
                "pixel_width": 1,
                "pixel_height": 1,
                "response_filename": f"{request_sha}.response.json",
            }
        )
    task = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_FULL_WORKER_TASK_V2",
        "protocol": "EXCLUSIVE_CANONICAL_JSON_RESPONSE_FILES_WITH_PUBLICATION_STATE_V2",
        "execution_nonce": nonce,
        "shard_id": 0,
        "provider_identity_sha256": "c" * 64,
        "word_box_normalization_authority": {},
        "cpu_threads": 6,
        "expected_environment": dict(os.environ),
        "execution_lease": {},
        "configuration": {"path": "/fixed", "sha256": "d" * 64, "size_bytes": 1},
        "models": [{}, {}],
        "max_request_count": 128,
        "requests": requests,
    }
    path = shard_root / "task.json"
    path.write_bytes(full_worker._canonical_bytes(task))
    return path, task


@pytest.mark.parametrize("count", [1, 128])
def test_full_worker_accepts_only_bounded_exact_runtime_batches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, count: int
) -> None:
    monkeypatch.setattr(full_worker, "FULL_RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(full_worker, "validate_normalization_authority", lambda value: value)
    monkeypatch.setattr(full_worker, "_validate_execution_lease", lambda value: None)
    monkeypatch.setattr(full_worker, "_validate_file_identity", lambda *args: None)
    monkeypatch.setattr(full_worker, "_validate_model_inventory", lambda value: None)
    path, task = _worker_task(tmp_path, count)
    assert full_worker._load_task(path) == task


def test_full_worker_rejects_129_typed_drift_and_wrong_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(full_worker, "FULL_RUNTIME_ROOT", tmp_path)
    monkeypatch.setattr(full_worker, "validate_normalization_authority", lambda value: value)
    monkeypatch.setattr(full_worker, "_validate_execution_lease", lambda value: None)
    monkeypatch.setattr(full_worker, "_validate_file_identity", lambda *args: None)
    monkeypatch.setattr(full_worker, "_validate_model_inventory", lambda value: None)
    path, task = _worker_task(tmp_path, 129)
    with pytest.raises(full_worker.FullReaderWorkerError):
        full_worker._load_task(path)
    path, task = _worker_task(tmp_path / "typed", 1)
    monkeypatch.setattr(full_worker, "FULL_RUNTIME_ROOT", tmp_path / "typed")
    task["max_request_count"] = 128.0
    path.write_bytes(full_worker._canonical_bytes(task))
    with pytest.raises(full_worker.FullReaderWorkerError):
        full_worker._load_task(path)
    task["max_request_count"] = 128
    wrong = tmp_path / "wrong" / "task.json"
    wrong.parent.mkdir()
    wrong.write_bytes(full_worker._canonical_bytes(task))
    with pytest.raises(full_worker.FullReaderWorkerError):
        full_worker._load_task(wrong)


def test_historical_sentinel_ledger_replays_and_tamper_fails() -> None:
    root = PROJECT_ROOT / "output/development/bank-corpus-wave-1-role-b-page-reader-v1/sentinel-v1"
    aggregate = json.loads((root / "sentinel-aggregate.json").read_bytes())
    control = json.loads((root / "sentinel-execution-control.json").read_bytes())
    full._validate_historical_sentinel_ledger(PROJECT_ROOT, aggregate, control)
    tampered = deepcopy(aggregate)
    tampered["executor_implementation_ledger"]["records"][0]["sha256"] = "0" * 64
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full._validate_historical_sentinel_ledger(PROJECT_ROOT, tampered, control)


def test_exact_aggregate_partitions_and_mutation() -> None:
    records = []
    records.extend(
        {
            "route": full._OCR_ROUTE,
            "origin": "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY",
            "request": {"render_specification": {"dpi": 200 if index < 20 else 300}},
        }
        for index in range(24)
    )
    records.extend(
        {
            "route": full._OCR_ROUTE,
            "origin": "PINNED_PPOCRV6_FULL_READER",
            "request": {"render_specification": {"dpi": 200 if index < 1230 else 300}},
        }
        for index in range(1332)
    )
    records.extend(
        {
            "route": full._NATIVE_ROUTE,
            "origin": "SEALED_CAUSAL_NATIVE_TEXT_GATE",
            "request": {"render_specification": None},
        }
        for _index in range(93)
    )
    accounting = full._exact_partition_accounting(records)
    assert accounting["routes"] == {full._OCR_ROUTE: 1356, full._NATIVE_ROUTE: 93}
    tampered = deepcopy(records)
    tampered[24]["request"]["render_specification"]["dpi"] = 300
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full._exact_partition_accounting(tampered)


def test_completed_native_resume_makes_zero_adapter_or_source_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    request_sha = "1" * 64
    document_id = "sha256:" + "a" * 64
    expected = _minimal_request(
        request_sha, route=full._NATIVE_ROUTE, ordinal=1, document_id=document_id
    )
    control = {"documents": [{"pages": [expected]}]}
    record = {"request_sha256": request_sha}
    monkeypatch.setattr(full, "_control_index", lambda _control: {request_sha: expected})
    monkeypatch.setattr(
        full, "_source_payload", lambda *args: (_ for _ in ()).throw(AssertionError())
    )
    assert full._run_native_requests(
        PROJECT_ROOT,
        {},
        control,
        {document_id: [record]},
        {document_id: "f" * 64},
    ) == {
        "status": "COMPLETE_NATIVE_RESUME_WITH_ZERO_NEW_READS",
        "native_read_request_count": 0,
    }


def test_native_adapter_refs_checkpoint_and_quarantine_accounting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from bctc_ai.ocr.causal_native_text_evidence_v1 import (
        build_causal_native_text_evidence,
    )

    document = fitz.open()
    page = document.new_page(width=300, height=200)
    page.insert_text((20, 40), "VISIBLE SYNTHETIC")
    page.insert_text((20, 80), "HIDDEN SECRET", color=(1, 1, 1))
    source_bytes = document.tobytes(garbage=4, deflate=True)
    document.close()
    for name in ("causal-native-text-v1.yaml", "native-text-quality-v2.yaml"):
        target = tmp_path / "config/ocr" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((PROJECT_ROOT / "config/ocr" / name).read_bytes())
    config_records = []
    for name in ("causal-native-text-v1.yaml", "native-text-quality-v2.yaml"):
        payload = (tmp_path / "config/ocr" / name).read_bytes()
        config_records.append(
            {
                "path": f"config/ocr/{name}",
                "sha256": sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    provider = {
        "config_records": config_records,
        "ocr_fallback_allowed": False,
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_binding_version": fitz.VersionBind,
        "pymupdf_distribution_version": distribution_version("PyMuPDF"),
        "pymupdf_runtime_versions": list(fitz.version),
    }
    provider["sha256"] = sha256(full._canonical_bytes(provider)).hexdigest()
    source_sha = sha256(source_bytes).hexdigest()
    request = {
        "bank_identity_used": False,
        "filename_used": False,
        "format_version": "BANK_CORPUS_WAVE_1_PAGE_READ_REQUEST_V1",
        "git_commit": "a" * 40,
        "historical_values_used": False,
        "implementation_ledger_sha256": "b" * 64,
        "input_ledger_sha256": "c" * 64,
        "physical_page": 1,
        "pre_ocr_feature_fingerprint_sha256": "d" * 64,
        "provider_identity_sha256": provider["sha256"],
        "render_runtime_identity_sha256": None,
        "render_specification": None,
        "role_a_used": False,
        "route": full._NATIVE_ROUTE,
        "route_plan_sha256": "e" * 64,
        "schema_used": False,
        "selection_receipt_sha256": "f" * 64,
        "sentinel_sha256": "0" * 64,
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
    }
    request_sha = sha256(full._canonical_bytes(request)).hexdigest()
    expected = {
        "request_ordinal": 1,
        "document_id": f"sha256:{source_sha}",
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
        "physical_page": 1,
        "route": full._NATIVE_ROUTE,
        "request_sha256": request_sha,
        "request": request,
    }
    control_identity = "f" * 64
    backend, result = build_causal_native_text_evidence(
        request=expected["request"],
        request_sha256=expected["request_sha256"],
        source_bytes=source_bytes,
        document_id=expected["document_id"],
        physical_page=expected["physical_page"],
        provider_runtime_ledger=provider,
        causal_policy_path=tmp_path / "config/ocr/causal-native-text-v1.yaml",
        quality_policy_path=tmp_path / "config/ocr/native-text-quality-v2.yaml",
        full_control_identity_sha256=control_identity,
    )
    monkeypatch.setattr(full, "OUTPUT_RELATIVE_ROOT", Path("full"))
    backend_ref = full._put_object(tmp_path, full._canonical_bytes(backend), suffix=".json")
    result_ref = full._put_object(tmp_path, full._canonical_bytes(result), suffix=".json")
    record = full._page_record(
        expected,
        status=result["status"],
        origin="SEALED_CAUSAL_NATIVE_TEXT_GATE",
        render_ref=None,
        backend_payload_ref=backend_ref,
        result_ref=result_ref,
        line_count=result["metrics"]["line_count"],
        word_token_count=result["metrics"]["word_token_count"],
        unresolved=result["status"] != "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
        quarantined_span_count=result["metrics"]["quarantined_span_count"],
    )
    control = {
        "control_identity_sha256": control_identity,
        "native_reader_contract": {
            "policy_path": "config/ocr/causal-native-text-v1.yaml",
            "quality_policy_path": "config/ocr/native-text-quality-v2.yaml",
        },
    }
    full._validate_page_record(tmp_path, control, record, expected)
    tampered = deepcopy(record)
    tampered["quarantined_span_count"] += 1
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full._validate_page_record(tmp_path, control, tampered, expected)


def test_docs_descendant_is_accepted_but_implementation_drift_is_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    relative = Path("impl.py")
    payload = b"stable implementation\n"
    (tmp_path / relative).write_bytes(payload)
    record = {
        "phase": "READ",
        "kind": "IMPLEMENTATION",
        "path": relative.as_posix(),
        "sha256": full.sha256_bytes(payload),
        "size_bytes": len(payload),
    }
    ledger = {"records": [record], "sha256": full._canonical_sha256([record])}
    published = {
        "executor_git": {"commit": "1" * 40, "dirty": False},
        "executor_implementation_ledger": ledger,
    }
    monkeypatch.setattr(full, "FULL_READER_IMPLEMENTATION_RELATIVE_PATHS", (relative,))
    monkeypatch.setattr(full, "_git_blob", lambda *args: payload)
    monkeypatch.setattr(
        full.sentinel,
        "_git_identity",
        lambda *args, **kwargs: {"commit": "2" * 40, "dirty": False},
    )

    class Result:
        returncode = 0

    monkeypatch.setattr(full.subprocess, "run", lambda *args, **kwargs: Result())
    full._validate_published_executor_on_descendant(tmp_path, published)
    (tmp_path / relative).write_bytes(b"drift\n")
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full._validate_published_executor_on_descendant(tmp_path, published)
