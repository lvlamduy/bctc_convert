from __future__ import annotations

import fcntl
import hashlib
import importlib.util
import json
import os
import stat
import subprocess
import time
from contextlib import nullcontext
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import fitz
import pytest

from bctc_ai.corpus.wave1_role_b_sentinel import (
    MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS,
    OUTPUT_RELATIVE_ROOT,
    POLICY_RELATIVE_PATH,
    SEALED_PLAN_RELATIVE_PATH,
    SEALED_PLAN_SHA256,
    SEALED_PLAN_SIZE_BYTES,
    WaveOneRoleBSentinelError,
    _assign_two_shards,
    _canonical_bytes,
    _checkpoint_payload,
    _consume_worker_response,
    _control_index,
    _document_locks,
    _execution_lease,
    _load_document_checkpoint,
    _load_policy,
    _publish_exclusive,
    _publish_missing_render_objects,
    _put_object,
    _read_object,
    _read_response_at,
    _render_exact_sentinel_sources,
    _run_pinned_workers,
    _scan_result_orphans,
    _sentinel_request_records,
)
from bctc_ai.rendering.page_reader import render_composited_displayed_page


def _sealed(project_root: Path) -> dict[str, object]:
    payload = (project_root / SEALED_PLAN_RELATIVE_PATH).read_bytes()
    assert len(payload) == SEALED_PLAN_SIZE_BYTES
    assert hashlib.sha256(payload).hexdigest() == SEALED_PLAN_SHA256
    assert _canonical_bytes(json.loads(payload)) == payload
    return json.loads(payload)


def _control_from_sealed(sealed: dict[str, object]) -> dict[str, object]:
    records = _sentinel_request_records(sealed)
    return {
        "control_identity_sha256": "c" * 64,
        "sharding": {"shards": _assign_two_shards(records)},
    }


def _valid_payload() -> dict[str, object]:
    return {
        "return_word_box": True,
        "rec_texts": ["Ngân hàng nguồn"],
        "rec_scores": [0.97],
        "rec_polys": [[[2, 2], [80, 2], [80, 20], [2, 20]]],
        "rec_boxes": [[2, 2, 80, 20]],
        "text_word_boxes": [[[2, 2, 40, 20], [41, 2, 80, 20]]],
        "text_word": [["Ngân hàng", "nguồn"]],
    }


def _synthetic_render(project_root: Path) -> dict[str, object]:
    document = fitz.open()
    page = document.new_page(width=72, height=72)
    page.insert_text((5, 30), "source-visible")
    rendered = render_composited_displayed_page(page, dpi=200)
    reference = _put_object(project_root, rendered.payload, suffix=".png")
    document.close()
    return {
        "payload": rendered.payload,
        "ref": reference,
        "pixel_width": rendered.pixel_width,
        "pixel_height": rendered.pixel_height,
        "dpi": rendered.dpi,
        "coordinate_authority": rendered.coordinate_authority,
    }


def _synthetic_result_fixture(
    project_root: Path,
    control: dict[str, object],
    expected: dict[str, object],
    render: dict[str, object],
) -> dict[str, object]:
    """NON_EVIDENCE synthetic protocol fixture under a pytest temporary root only."""

    response = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_RESPONSE_V1",
        "execution_nonce": "e" * 64,
        "shard_id": 0,
        "request_sha256": expected["request_sha256"],
        "render_sha256": render["ref"]["sha256"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "payload": _valid_payload(),
        "observational": {
            "model_load_wall_seconds": 1.25,
            "inference_wall_seconds": 0.5,
        },
    }
    record, observation = _consume_worker_response(
        project_root,
        control,
        expected,
        render,
        _canonical_bytes(response),
        execution_nonce="e" * 64,
        shard_id=0,
    )
    assert observation == response["observational"]
    return record


def test_real_sealed_plan_exact_two_shards_and_no_metadata_projection(
    project_root: Path,
) -> None:
    sealed = _sealed(project_root)
    records = _sentinel_request_records(sealed)
    shards = _assign_two_shards(records)
    assert len(records) == 24
    assert len({record["document_id"] for record in records}) == 14
    assert [(shard["document_count"], shard["request_count"]) for shard in shards] == [
        (7, 12),
        (7, 12),
    ]
    assert [[record["sentinel_ordinal"] for record in shard["requests"]] for shard in shards] == [
        [3, 4, 5, 7, 9, 10, 11, 12, 14, 16, 21, 22],
        [1, 2, 6, 8, 13, 15, 17, 18, 19, 20, 23, 24],
    ]
    assert all(not ({"bank", "relative_path", "filename"} & set(record)) for record in records)
    metadata_mutation = deepcopy(sealed)
    for sentinel in metadata_mutation["sentinel"]:
        sentinel["bank"] = "IGNORED_REGISTRY_METADATA"
    assert _assign_two_shards(_sentinel_request_records(metadata_mutation)) == shards


def test_policy_is_exact_and_binds_scrubbed_worker_environment(project_root: Path) -> None:
    policy = _load_policy(project_root)
    assert policy["sealed_plan"]["sha256"] == SEALED_PLAN_SHA256
    assert policy["worker"]["process_count_initial_run"] == 2
    assert policy["worker"]["environment"]["PYTHONNOUSERSITE"] == "1"
    assert "HOME" in policy["worker"]["isolated_runtime_directories"]
    assert "PYTHONPATH" not in policy["worker"]["environment"]
    assert (project_root / POLICY_RELATIVE_PATH).is_file()


def test_b_implementation_ledger_covers_exact_internal_import_closure(
    project_root: Path,
) -> None:
    source = """
import json, runpy, sys
import bctc_ai.corpus.wave1_role_b_sentinel
runpy.run_path('scripts/models/run_ppocrv6_sentinel_worker.py')
runpy.run_path('scripts/corpus/run_wave1_role_b_sentinel.py')
print(json.dumps(sorted({m.__file__ for n,m in sys.modules.items() if n.startswith('bctc_ai') and getattr(m,'__file__',None)})))
"""
    output = subprocess.run(
        [project_root / ".venv/bin/python", "-c", source],
        cwd=project_root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    imported = {Path(path).relative_to(project_root).as_posix() for path in json.loads(output)}
    ledgered_internal = {
        path.as_posix()
        for path in MILESTONE_B_IMPLEMENTATION_RELATIVE_PATHS
        if path.as_posix().startswith("src/")
    }
    assert imported == ledgered_internal


def test_content_objects_reject_intermediate_write_and_read_symlinks(
    tmp_path: Path,
) -> None:
    outside = tmp_path / "outside"
    outside.mkdir()
    sentinel_parent = tmp_path / OUTPUT_RELATIVE_ROOT.parent
    sentinel_parent.mkdir(parents=True)
    (sentinel_parent / OUTPUT_RELATIVE_ROOT.name).symlink_to(outside, target_is_directory=True)
    with pytest.raises(WaveOneRoleBSentinelError, match="symlink|without links"):
        _put_object(tmp_path, b"evidence", suffix=".json")
    assert list(outside.iterdir()) == []

    (sentinel_parent / OUTPUT_RELATIVE_ROOT.name).unlink()
    output = tmp_path / OUTPUT_RELATIVE_ROOT
    output.mkdir()
    objects_outside = outside / "objects"
    digest = hashlib.sha256(b"evidence").hexdigest()
    target = objects_outside / "sha256" / digest[:2] / f"{digest}.json"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"evidence")
    target.chmod(0o444)
    (output / "objects").symlink_to(objects_outside, target_is_directory=True)
    reference = {
        "path": f"objects/sha256/{digest[:2]}/{digest}.json",
        "sha256": digest,
        "size_bytes": 8,
    }
    with pytest.raises(WaveOneRoleBSentinelError, match="without links"):
        _read_object(tmp_path, reference, ".json")


def test_full_request_orphan_adoption_and_checkpoint_resume_are_exact(
    project_root: Path,
    tmp_path: Path,
) -> None:
    control = _control_from_sealed(_sealed(project_root))
    expected = _control_index(control)[next(iter(_control_index(control)))]
    render = _synthetic_render(tmp_path)
    record = _synthetic_result_fixture(tmp_path, control, expected, render)
    renders = {expected["request_sha256"]: render}
    adopted = _scan_result_orphans(
        tmp_path,
        control,
        expected["document_id"],
        [],
        renders,
    )
    assert adopted == [record]
    from bctc_ai.corpus.wave1_role_b_sentinel import _publish_checkpoint

    checkpoint, digest = _publish_checkpoint(
        tmp_path,
        control,
        expected["document_id"],
        [record],
        None,
    )
    assert checkpoint["generation"] == 1
    checkpoint_file = (
        tmp_path
        / OUTPUT_RELATIVE_ROOT
        / "checkpoints"
        / expected["source_sha256"]
        / f"0001-{digest}.json"
    )
    checkpoint_temp = checkpoint_file.with_name(f".{checkpoint_file.name}.{'d' * 32}.tmp")
    os.link(checkpoint_file, checkpoint_temp)
    assert checkpoint_file.stat().st_nlink == 2
    loaded, loaded_digest = _load_document_checkpoint(
        tmp_path,
        control,
        expected["document_id"],
        renders,
    )
    assert loaded == [record]
    assert loaded_digest == digest
    assert not checkpoint_temp.exists()
    assert checkpoint_file.stat().st_nlink == 1


def test_checkpoint_resume_quarantines_only_exact_interrupted_temp(
    project_root: Path,
    tmp_path: Path,
) -> None:
    control = _control_from_sealed(_sealed(project_root))
    expected = next(iter(_control_index(control).values()))
    source_sha = expected["source_sha256"]
    directory = tmp_path / OUTPUT_RELATIVE_ROOT / "checkpoints" / source_sha
    directory.mkdir(parents=True)
    temporary = directory / f".0001-{'a' * 64}.json.{'b' * 32}.tmp"
    temporary.write_bytes(b"interrupted")
    temporary.chmod(0o600)
    assert _load_document_checkpoint(
        tmp_path,
        control,
        expected["document_id"],
        {},
    ) == ([], None)
    (directory / "foreign.tmp").write_bytes(b"foreign")
    with pytest.raises(WaveOneRoleBSentinelError, match="foreign"):
        _load_document_checkpoint(
            tmp_path,
            control,
            expected["document_id"],
            {},
        )


def test_result_replay_rejects_same_count_text_and_backend_metadata_tamper(
    project_root: Path,
    tmp_path: Path,
) -> None:
    from bctc_ai.corpus.wave1_role_b_sentinel import _json_object, _validate_result_record

    control = _control_from_sealed(_sealed(project_root))
    expected = next(iter(_control_index(control).values()))
    render = _synthetic_render(tmp_path)
    record = _synthetic_result_fixture(tmp_path, control, expected, render)
    result = _json_object(
        _read_object(tmp_path, record["result_ref"], ".json"),
        "fixture result",
    )
    result["lines"][0]["raw_text"] = "fabricated-same-count"
    tampered_result_ref = _put_object(tmp_path, _canonical_bytes(result), suffix=".json")
    tampered = {**record, "result_ref": tampered_result_ref}
    with pytest.raises(WaveOneRoleBSentinelError, match="projection"):
        _validate_result_record(tmp_path, tampered, expected, render)

    backend = _json_object(
        _read_object(tmp_path, record["backend_payload_ref"], ".json"),
        "fixture backend",
    )
    backend["bank"] = "forbidden-metadata"
    tampered_backend_ref = _put_object(tmp_path, _canonical_bytes(backend), suffix=".json")
    tampered = {**record, "backend_payload_ref": tampered_backend_ref}
    with pytest.raises(WaveOneRoleBSentinelError, match="identity|embedded"):
        _validate_result_record(tmp_path, tampered, expected, render)


def test_complete_resume_path_starts_zero_workers(project_root: Path) -> None:
    control = _control_from_sealed(_sealed(project_root))
    complete = {request["document_id"]: [] for request in _control_index(control).values()}
    for request in _control_index(control).values():
        complete[request["document_id"]].append({"request_sha256": request["request_sha256"]})
    result = _run_pinned_workers(
        project_root,
        Path("unused"),
        {},
        {},
        control,
        {},
        complete,
        {document_id: "f" * 64 for document_id in complete},
        -1,
    )
    assert result == {
        "status": "COMPLETE_RESUME_WITH_ZERO_INFERENCE",
        "worker_process_count": 0,
        "inference_request_count": 0,
        "observational_runtime_path": None,
    }


def test_document_lock_name_drift_releases_fd_for_fresh_resume(tmp_path: Path) -> None:
    document_id = f"sha256:{'1' * 64}"
    lock = tmp_path / OUTPUT_RELATIVE_ROOT / "locks" / f"{'1' * 64}.lock"
    with pytest.raises(WaveOneRoleBSentinelError, match="identity"):
        with _document_locks(tmp_path, [document_id]):
            lock.unlink()
    with _document_locks(tmp_path, [document_id]):
        assert lock.exists()


def _load_worker(project_root: Path):
    path = project_root / "scripts/models/run_ppocrv6_sentinel_worker.py"
    specification = importlib.util.spec_from_file_location("sentinel_worker_test", path)
    assert specification is not None and specification.loader is not None
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def test_worker_full_model_inventory_rejects_extra_and_symlink(
    project_root: Path,
    tmp_path: Path,
) -> None:
    worker = _load_worker(project_root)
    model = tmp_path / "model"
    model.mkdir()
    payload = b"model"
    (model / "weights.bin").write_bytes(payload)
    contract = {
        "key": "fixture",
        "directory": model.as_posix(),
        "files": [
            {
                "path": "weights.bin",
                "sha256": hashlib.sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        ],
    }
    worker._validate_model_inventory(contract)
    (model / "extra.bin").write_bytes(b"extra")
    with pytest.raises(worker.SentinelWorkerError, match="full model inventory"):
        worker._validate_model_inventory(contract)
    (model / "extra.bin").unlink()
    (model / "link.bin").symlink_to(model / "weights.bin")
    with pytest.raises(worker.SentinelWorkerError, match="symlink"):
        worker._validate_model_inventory(contract)


def test_worker_requires_exact_inherited_execution_lease(
    project_root: Path,
    tmp_path: Path,
) -> None:
    worker = _load_worker(project_root)
    with _execution_lease(tmp_path) as lease_fd:
        identity = os.fstat(lease_fd)
        lease = {"fd": lease_fd, "device": identity.st_dev, "inode": identity.st_ino}
        worker._validate_execution_lease(lease)
        with pytest.raises(worker.SentinelWorkerError, match="identity drifted"):
            worker._validate_execution_lease({**lease, "inode": identity.st_ino + 1})


def test_worker_predicts_literal_held_fd_and_rehashes_same_inode(
    project_root: Path,
    tmp_path: Path,
) -> None:
    worker = _load_worker(project_root)
    image = tmp_path / "render.png"
    image.write_bytes(b"held-render")
    image.chmod(0o444)
    observed = {}

    class Result:
        json = {"res": _valid_payload()}

    class Pipeline:
        def predict(self, path, **_kwargs):
            observed["path"] = path
            with open(path, "rb") as stream:
                observed["bytes"] = stream.read()
            return [Result()]

    class Session:
        _pipeline = Pipeline()

    descriptor = worker._open_image_fd(
        image,
        hashlib.sha256(b"held-render").hexdigest(),
        len(b"held-render"),
    )
    try:
        payload, _elapsed = worker._predict_from_held_render(
            Session(),
            descriptor,
            pixel_width=200,
            pixel_height=200,
        )
        worker._revalidate_held_render(
            descriptor,
            expected_sha256=hashlib.sha256(b"held-render").hexdigest(),
            expected_size=len(b"held-render"),
        )
    finally:
        os.close(descriptor)
    assert observed == {"path": f"/proc/self/fd/{descriptor}", "bytes": b"held-render"}
    assert payload["rec_texts"] == ["Ngân hàng nguồn"]


def test_checkpoint_payload_rejects_foreign_request(project_root: Path) -> None:
    control = _control_from_sealed(_sealed(project_root))
    document_id = next(iter(_control_index(control).values()))["document_id"]
    with pytest.raises(WaveOneRoleBSentinelError, match="foreign"):
        _checkpoint_payload(
            control,
            document_id,
            [{"request_sha256": "0" * 64, "sentinel_ordinal": 1}],
            None,
        )


def test_owned_nlink_two_crash_windows_recover_exact_temps(tmp_path: Path) -> None:
    payload = b"immutable-object"
    reference = _put_object(tmp_path, payload, suffix=".json")
    final = tmp_path / OUTPUT_RELATIVE_ROOT / reference["path"]
    object_temp = final.with_name(f".{final.name}.{'a' * 32}.tmp")
    os.link(final, object_temp)
    assert final.stat().st_nlink == 2
    assert _put_object(tmp_path, payload, suffix=".json") == reference
    assert not object_temp.exists()
    assert final.stat().st_nlink == 1

    published = _publish_exclusive(
        tmp_path,
        OUTPUT_RELATIVE_ROOT,
        "fixture.json",
        b"published",
    )
    publication_temp = published.with_name(f".{published.name}.{'b' * 32}.tmp")
    os.link(published, publication_temp)
    assert published.stat().st_nlink == 2
    _publish_exclusive(tmp_path, OUTPUT_RELATIVE_ROOT, "fixture.json", b"published")
    assert not publication_temp.exists()
    assert published.stat().st_nlink == 1

    response_directory = tmp_path / "response"
    response_directory.mkdir()
    response = response_directory / "request.response.json"
    response.write_bytes(b"response")
    response.chmod(0o444)
    response_temp = response.with_name(f".{response.name}.{'c' * 32}.tmp")
    os.link(response, response_temp)
    directory_fd = os.open(response_directory, os.O_RDONLY | os.O_DIRECTORY)
    try:
        assert _read_response_at(directory_fd, response.name) == b"response"
    finally:
        os.close(directory_fd)
    assert not response_temp.exists()
    assert response.stat().st_nlink == 1


def _mini_render_inputs(tmp_path: Path) -> tuple[dict[str, object], dict[str, object]]:
    document = fitz.open()
    for page_number in range(1, 25):
        page = document.new_page(width=72, height=72)
        page.insert_text((5, 30), f"page {page_number}")
    source = tmp_path / "source.pdf"
    document.save(source)
    document.close()
    source_payload = source.read_bytes()
    source_sha = hashlib.sha256(source_payload).hexdigest()
    document_id = f"sha256:{source_sha}"
    records = []
    for ordinal in range(1, 25):
        request_sha = hashlib.sha256(f"request-{ordinal}".encode()).hexdigest()
        records.append(
            {
                "sentinel_ordinal": ordinal,
                "document_id": document_id,
                "source_sha256": source_sha,
                "source_size_bytes": len(source_payload),
                "physical_page": ordinal,
                "request_sha256": request_sha,
                "request": {
                    "render_specification": {
                        "source": "FULL_COMPOSITED_DISPLAYED_PDF_PAGE",
                        "dpi": 200,
                        "colorspace": "RGB",
                        "alpha": False,
                        "annotations": "INCLUDED",
                    }
                },
            }
        )
    sealed = {
        "documents": [
            {
                "document_id": document_id,
                "relative_path": "source.pdf",
                "sha256": source_sha,
                "size_bytes": len(source_payload),
                "page_count": 24,
            }
        ]
    }
    control = {
        "sharding": {
            "shards": [
                {"requests": records[:12]},
                {"requests": records[12:]},
            ]
        }
    }
    return sealed, control


def test_render_publication_and_verify_modes_are_distinct_and_read_only(
    tmp_path: Path,
) -> None:
    sealed, control = _mini_render_inputs(tmp_path)
    renders = _render_exact_sentinel_sources(
        tmp_path,
        sealed,
        control,
        require_existing=False,
    )
    assert len(renders) == 24
    assert not (tmp_path / OUTPUT_RELATIVE_ROOT).exists()
    with pytest.raises(WaveOneRoleBSentinelError, match="absent"):
        _render_exact_sentinel_sources(
            tmp_path,
            sealed,
            control,
            require_existing=True,
        )
    assert not (tmp_path / OUTPUT_RELATIVE_ROOT).exists()

    _publish_missing_render_objects(tmp_path, renders, set())
    for render in renders.values():
        path = tmp_path / OUTPUT_RELATIVE_ROOT / render["ref"]["path"]
        assert path.read_bytes() == render["payload"]
        assert stat.S_IMODE(path.stat().st_mode) == 0o444
    snapshot = {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }
    replay = _render_exact_sentinel_sources(
        tmp_path,
        sealed,
        control,
        require_existing=True,
    )
    assert {key: value["ref"] for key, value in replay.items()} == {
        key: value["ref"] for key, value in renders.items()
    }
    assert snapshot == {
        path.relative_to(tmp_path): (path.stat().st_size, path.stat().st_mtime_ns)
        for path in tmp_path.rglob("*")
        if path.is_file()
    }


def test_capacity_gate_precedes_any_production_publication(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bctc_ai.corpus.wave1_role_b_sentinel as sentinel

    monkeypatch.setattr(
        sentinel,
        "_authenticate_sealed_plan",
        lambda *_args, **_kwargs: ({}, {"execution": {"minimum_free_space_bytes": 123}}, {}),
    )
    observed = []

    def blocked_capacity(*_args, **_kwargs):
        observed.append("capacity")
        raise WaveOneRoleBSentinelError("capacity blocked")

    monkeypatch.setattr(sentinel, "_ensure_capacity", blocked_capacity)
    monkeypatch.setattr(
        sentinel,
        "_publish_exclusive",
        lambda *_args, **_kwargs: observed.append("publish"),
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="capacity"):
        sentinel.run_authenticated_sentinel(tmp_path, model_cache=tmp_path / "models")
    assert observed == ["capacity"]
    assert not (tmp_path / OUTPUT_RELATIVE_ROOT).exists()


def test_cli_reports_logical_identity_separately_from_artifact_hash(
    project_root: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = project_root / "scripts/corpus/run_wave1_role_b_sentinel.py"
    specification = importlib.util.spec_from_file_location("sentinel_cli_test", path)
    assert specification is not None and specification.loader is not None
    cli = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(cli)
    aggregate = {
        "status": "COMPLETE_AUTHENTICATED_WAVE_1_24_PAGE_OCR_SENTINEL",
        "aggregate_identity_sha256": "1" * 64,
        "accounting": {"request_count": 24},
    }
    monkeypatch.setattr(
        cli,
        "parse_args",
        lambda: SimpleNamespace(command="finalize", model_cache=Path("unused")),
    )
    monkeypatch.setattr(cli, "finalize_authenticated_sentinel", lambda *_args, **_kwargs: aggregate)
    assert cli.main() == 0
    summary = json.loads(capsys.readouterr().out)
    artifact = _canonical_bytes(aggregate)
    assert summary["aggregate_identity_sha256"] == "1" * 64
    assert summary["artifact_sha256"] == hashlib.sha256(artifact).hexdigest()
    assert summary["artifact_size_bytes"] == len(artifact)
    assert summary["artifact_sha256"] != summary["aggregate_identity_sha256"]


def test_non_evidence_initial_supervisor_launches_exact_two_twelve_page_processes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NON_EVIDENCE fake-process harness; it cannot call any production API/finalizer."""

    import bctc_ai.corpus.wave1_role_b_sentinel as sentinel

    (tmp_path / "NON_EVIDENCE_TEST_ONLY").write_text("no production publication\n")
    interpreter = tmp_path / "python.bin"
    interpreter.write_bytes(b"pinned-interpreter")
    worker = tmp_path / "worker.py"
    worker.write_text("# non-evidence fake; never executed\n")
    requests = [
        {
            "sentinel_ordinal": ordinal,
            "request_sha256": hashlib.sha256(f"worker-{ordinal}".encode()).hexdigest(),
            "document_id": f"sha256:{ordinal:064x}",
        }
        for ordinal in range(1, 25)
    ]
    control = {
        "sharding": {
            "shards": [
                {"shard_id": 0, "requests": requests[:12]},
                {"shard_id": 1, "requests": requests[12:]},
            ]
        }
    }
    sealed = {
        "ppocrv6_runtime_model_ledger": {
            "runtime_interpreter_target_sha256": hashlib.sha256(b"pinned-interpreter").hexdigest(),
            "runtime_interpreter_target_size_bytes": len(b"pinned-interpreter"),
        }
    }
    policy = {
        "execution": {"minimum_free_space_bytes": 0},
        "worker": {"interpreter": "python.bin", "script": "worker.py"},
    }
    renders = {request["request_sha256"]: {} for request in requests}
    records_by_document = {request["document_id"]: [] for request in requests}
    checkpoints = {request["document_id"]: None for request in requests}
    tasks: dict[int, list[dict[str, object]]] = {}
    launches = []

    monkeypatch.setattr(sentinel, "_ensure_capacity", lambda *_args: None)
    monkeypatch.setattr(
        sentinel,
        "_worker_environment",
        lambda *_args: {"NON_EVIDENCE_TEST_ONLY": "1"},
    )

    def fake_task(
        _project_root,
        _model_cache,
        _sealed,
        shard_id,
        shard_requests,
        _renders,
        _nonce,
        _environment,
        _execution_lease_fd,
    ):
        tasks[shard_id] = shard_requests
        return {"non_evidence": True, "shard_id": shard_id}

    monkeypatch.setattr(sentinel, "_build_worker_task", fake_task)

    class FakeProcess:
        returncode = 0

        def __init__(self, arguments, **kwargs):
            response_directory = Path(arguments[arguments.index("--response-directory") + 1])
            shard_id = int(response_directory.parent.name.removeprefix("shard-"))
            assert kwargs["pass_fds"] == (lease_fd,)
            launches.append(shard_id)
            for request in tasks[shard_id]:
                response = response_directory / f"{request['request_sha256']}.response.json"
                response.write_bytes(b"{}\n")
                response.chmod(0o444)

        def poll(self):
            return 0

        def terminate(self):  # pragma: no cover - success path does not terminate
            raise AssertionError("fake success process was terminated")

    monkeypatch.setattr(sentinel.subprocess, "Popen", FakeProcess)
    monkeypatch.setattr(
        sentinel,
        "_consume_worker_response",
        lambda _root, _control, expected, _render, _payload, **_kwargs: (
            {
                "request_sha256": expected["request_sha256"],
                "sentinel_ordinal": expected["sentinel_ordinal"],
            },
            {"model_load_wall_seconds": 0.0, "inference_wall_seconds": 0.0},
        ),
    )
    monkeypatch.setattr(
        sentinel,
        "_publish_checkpoint",
        lambda _root, _control, _document, records, _previous: (
            {"generation": len(records)},
            hashlib.sha256(str(len(records)).encode()).hexdigest(),
        ),
    )
    monkeypatch.setattr(sentinel, "_append_observational_timing", lambda *_args: None)
    with sentinel._execution_lease(tmp_path) as lease_fd:
        result = _run_pinned_workers(
            tmp_path,
            tmp_path / "models",
            sealed,
            policy,
            control,
            renders,
            records_by_document,
            checkpoints,
            lease_fd,
        )
    assert launches == [0, 1]
    assert [len(tasks[index]) for index in (0, 1)] == [12, 12]
    assert result["worker_process_count"] == 2
    assert result["inference_request_count"] == 24
    assert not (tmp_path / OUTPUT_RELATIVE_ROOT / "sentinel-aggregate.json").exists()
    assert not (tmp_path / OUTPUT_RELATIVE_ROOT / "sentinel-execution-control.json").exists()


@pytest.mark.skipif(not Path("/proc").is_dir(), reason="Linux inherited-flock contract")
def test_supervisor_crash_keeps_global_lease_until_inherited_worker_exits(
    project_root: Path,
    tmp_path: Path,
) -> None:
    source = f"""
import os, subprocess, sys
from pathlib import Path
sys.path.insert(0, {str(project_root / "src")!r})
from bctc_ai.corpus.wave1_role_b_sentinel import _execution_lease
root=Path({str(tmp_path)!r})
with _execution_lease(root) as lease_fd:
    child=subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(1.5)'], pass_fds=(lease_fd,), close_fds=True)
    print(child.pid, flush=True)
    os._exit(0)
"""
    supervisor = subprocess.Popen(
        [project_root / ".venv/bin/python", "-c", source],
        cwd=project_root,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert supervisor.stdout is not None
    child_pid = int(supervisor.stdout.readline().strip())
    assert supervisor.wait(timeout=5) == 0
    lease_path = tmp_path / OUTPUT_RELATIVE_ROOT / "locks/sentinel-execution.lease"
    lease_fd = os.open(lease_path, os.O_RDWR | os.O_NOFOLLOW)
    try:
        with pytest.raises(BlockingIOError):
            fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        deadline = time.monotonic() + 5
        while True:
            try:
                fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    os.kill(child_pid, 9)
                    pytest.fail("inherited worker did not release execution lease")
                time.sleep(0.05)
        fcntl.flock(lease_fd, fcntl.LOCK_UN)
    finally:
        os.close(lease_fd)


def test_synthetic_complete_aggregate_is_deterministic_and_artifact_hash_is_exact(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """NON_EVIDENCE aggregate assembly fixture; no OCR/provider is invoked."""

    import bctc_ai.corpus.wave1_role_b_sentinel as sentinel

    control = _control_from_sealed(_sealed(project_root))
    control.update(
        {
            "sealed_plan": {
                "path": SEALED_PLAN_RELATIVE_PATH.as_posix(),
                "sha256": SEALED_PLAN_SHA256,
            },
            "executor_git": {"commit": "2" * 40, "dirty": False},
            "executor_implementation_ledger": {"records": [], "sha256": "3" * 64},
        }
    )
    index = _control_index(control)
    records_by_document: dict[str, list[dict[str, object]]] = {}
    for expected in index.values():
        records_by_document.setdefault(expected["document_id"], []).append(
            {
                "sentinel_ordinal": expected["sentinel_ordinal"],
                "request_sha256": expected["request_sha256"],
                "status": "OCR_WORD_BOX_READ_COMPLETE",
                "line_count": expected["sentinel_ordinal"],
                "word_token_count": expected["sentinel_ordinal"] + 1,
            }
        )
    sealed = {
        "ppocrv6_runtime_model_ledger": {"sha256": "4" * 64},
        "render_runtime_ledger": {"sha256": "5" * 64},
    }
    policy = {"claim_boundary": "EXACT_24_PAGE_OCR_SENTINEL_SOURCE_TEXT_AND_GEOMETRY_ONLY"}
    executor = {
        "git": control["executor_git"],
        "implementation_ledger": control["executor_implementation_ledger"],
    }
    monkeypatch.setattr(
        sentinel,
        "_authenticate_sealed_plan",
        lambda *_args, **_kwargs: (sealed, policy, executor),
    )
    monkeypatch.setattr(sentinel, "build_authenticated_control", lambda *_args, **_kwargs: control)
    monkeypatch.setattr(sentinel, "_read_published_control", lambda *_args: None)
    monkeypatch.setattr(sentinel, "_document_locks", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(
        sentinel,
        "_render_exact_sentinel_sources",
        lambda *_args, **_kwargs: {},
    )
    monkeypatch.setattr(
        sentinel,
        "_load_document_checkpoint",
        lambda _root, _control, document_id, _renders: (
            records_by_document[document_id],
            hashlib.sha256(document_id.encode()).hexdigest(),
        ),
    )
    monkeypatch.setattr(
        sentinel,
        "_final_checkpoint_ref",
        lambda _root, document_id, generation, digest: {
            "path": f"checkpoints/{document_id.removeprefix('sha256:')}/{generation:04d}-{digest}.json",
            "sha256": digest,
            "size_bytes": generation,
        },
    )
    first = sentinel.verify_authenticated_sentinel(tmp_path, model_cache=tmp_path / "models")
    second = sentinel.verify_authenticated_sentinel(tmp_path, model_cache=tmp_path / "models")
    assert _canonical_bytes(first) == _canonical_bytes(second)
    assert first["aggregate_identity_sha256"] == sentinel._canonical_sha256(
        {key: value for key, value in first.items() if key != "aggregate_identity_sha256"}
    )

    finalized = sentinel.finalize_authenticated_sentinel(
        tmp_path,
        model_cache=tmp_path / "models",
    )
    artifact = tmp_path / OUTPUT_RELATIVE_ROOT / "sentinel-aggregate.json"
    assert artifact.read_bytes() == _canonical_bytes(finalized)
    assert stat.S_IMODE(artifact.stat().st_mode) == 0o444
    assert (
        hashlib.sha256(artifact.read_bytes()).hexdigest()
        == hashlib.sha256(_canonical_bytes(finalized)).hexdigest()
    )
    assert (
        hashlib.sha256(artifact.read_bytes()).hexdigest() != finalized["aggregate_identity_sha256"]
    )
