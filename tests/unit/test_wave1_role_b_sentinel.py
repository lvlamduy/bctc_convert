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
    _create_runtime_root,
    _document_locks,
    _execution_lease,
    _load_document_checkpoint,
    _load_policy,
    _materialize_private_shard_inputs,
    _normalization_authority,
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
from bctc_ai.corpus.wave1_role_b_word_box_normalization import (
    WORD_BOX_NORMALIZATION_POLICY,
    normalization_policy_sha256,
    normalize_ppocrv6_word_boxes,
)
from bctc_ai.rendering.page_reader import render_composited_displayed_page


def _sealed(project_root: Path) -> dict[str, object]:
    payload = (project_root / SEALED_PLAN_RELATIVE_PATH).read_bytes()
    assert len(payload) == SEALED_PLAN_SIZE_BYTES
    assert hashlib.sha256(payload).hexdigest() == SEALED_PLAN_SHA256
    assert _canonical_bytes(json.loads(payload)) == payload
    return json.loads(payload)


def _normalization_control() -> dict[str, object]:
    return {
        "control_identity_sha256": "c" * 64,
        "executor_implementation_ledger": {"records": [], "sha256": "d" * 64},
        "word_box_normalization": {
            "policy": deepcopy(WORD_BOX_NORMALIZATION_POLICY),
            "policy_sha256": normalization_policy_sha256(WORD_BOX_NORMALIZATION_POLICY),
            "normalization_producer_implementation_ledger_sha256": "d" * 64,
        },
    }


def _control_from_sealed(sealed: dict[str, object]) -> dict[str, object]:
    records = _sentinel_request_records(sealed)
    return {
        **_normalization_control(),
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

    _normalized, normalization_ledger = normalize_ppocrv6_word_boxes(
        _valid_payload(),
        pixel_width=render["pixel_width"],
        pixel_height=render["pixel_height"],
        authority=_normalization_authority(control),
    )
    response = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_RESPONSE_V2",
        "execution_nonce": "e" * 64,
        "shard_id": 0,
        "request_sha256": expected["request_sha256"],
        "render_sha256": render["ref"]["sha256"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "payload": _valid_payload(),
        "word_box_normalization_ledger": normalization_ledger,
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
    assert (
        policy["worker"]["provider_input_materialization"]
        == "PER_SHARD_PRIVATE_IMMUTABLE_PNG_COPY_V1"
    )
    assert policy["worker"]["provider_input_filename"] == "REQUEST_SHA256_DOT_PNG"
    assert policy["worker"]["provider_input_mode"] == "0444"
    assert policy["worker"]["provider_input_hardlink_to_evidence_allowed"] is False
    assert policy["word_box_normalization"] == WORD_BOX_NORMALIZATION_POLICY
    assert "HOME" in policy["worker"]["isolated_runtime_directories"]
    assert "PYTHONPATH" not in policy["worker"]["environment"]
    assert (project_root / POLICY_RELATIVE_PATH).is_file()


def test_normalization_authority_rejects_valid_hash_producer_ledger_mismatch() -> None:
    control = _normalization_control()
    control["word_box_normalization"]["normalization_producer_implementation_ledger_sha256"] = (
        "e" * 64
    )

    with pytest.raises(WaveOneRoleBSentinelError, match="producer ledger binding"):
        _normalization_authority(control)


@pytest.mark.parametrize(
    ("source", "replacement"),
    [
        (
            "maximum_per_edge_overshoot_pixels: 1",
            "maximum_per_edge_overshoot_pixels: true",
        ),
        (
            "maximum_per_edge_overshoot_pixels: 1",
            "maximum_per_edge_overshoot_pixels: 1.0",
        ),
        ("raw_provider_payload_preserved: true", "raw_provider_payload_preserved: 1"),
        ("process_count_initial_run: 2", "process_count_initial_run: 2.0"),
        (
            "production_authentication_bypass_allowed: false",
            "production_authentication_bypass_allowed: 0",
        ),
    ],
)
def test_policy_loader_rejects_typed_policy_drift(
    project_root: Path,
    tmp_path: Path,
    source: str,
    replacement: str,
) -> None:
    target = tmp_path / POLICY_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    target.write_text(
        (project_root / POLICY_RELATIVE_PATH)
        .read_text(encoding="utf-8")
        .replace(source, replacement),
        encoding="utf-8",
    )

    with pytest.raises(WaveOneRoleBSentinelError, match="policy.*drifted"):
        _load_policy(tmp_path)


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
    no_change_result = json.loads(_read_object(tmp_path, record["result_ref"], ".json"))
    assert no_change_result["word_box_normalization_ledger"]["status"] == "NO_CHANGE"
    assert all(
        set(word)
        == {
            "raw_text",
            "score",
            "score_kind",
            "normalized_pixel_bbox",
            "canonical_bbox_mpt",
            "canonical_polygon_mpt",
        }
        for word in [
            *no_change_result["words"],
            *(word for line in no_change_result["lines"] for word in line["words"]),
        ]
    )
    _put_object(
        tmp_path,
        _canonical_bytes(
            {
                "format_version": "BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READ_RESULT_V1",
                "request_sha256": expected["request_sha256"],
            }
        ),
        suffix=".json",
    )
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


def test_corrected_worker_response_preserves_raw_backend_and_projects_normalized_result(
    project_root: Path,
    tmp_path: Path,
) -> None:
    control = _control_from_sealed(_sealed(project_root))
    expected = next(iter(_control_index(control).values()))
    render = _synthetic_render(tmp_path)
    width = render["pixel_width"]
    payload = {
        "return_word_box": True,
        "rec_texts": ["edge"],
        "rec_scores": [0.99],
        "rec_polys": [[[width - 20, 10], [width, 10], [width, 30], [width - 20, 30]]],
        "rec_boxes": [[width - 20, 10, width, 30]],
        "text_word_boxes": [[[width - 10, 10, width + 1, 30]]],
        "text_word": [["edge"]],
    }
    normalized, ledger = normalize_ppocrv6_word_boxes(
        payload,
        pixel_width=width,
        pixel_height=render["pixel_height"],
        authority=_normalization_authority(control),
    )
    response = {
        "format_version": "BANK_CORPUS_WAVE_1_PPOCRV6_WORKER_RESPONSE_V2",
        "execution_nonce": "e" * 64,
        "shard_id": 0,
        "request_sha256": expected["request_sha256"],
        "render_sha256": render["ref"]["sha256"],
        "provider_identity_sha256": expected["request"]["provider_identity_sha256"],
        "payload": payload,
        "word_box_normalization_ledger": ledger,
        "observational": {
            "model_load_wall_seconds": 1.25,
            "inference_wall_seconds": 0.5,
        },
    }

    typed_worker_ledger = deepcopy(response)
    typed_worker_ledger["word_box_normalization_ledger"]["correction_count"] = 1.0
    with pytest.raises(WaveOneRoleBSentinelError, match="parent replay"):
        _consume_worker_response(
            tmp_path,
            control,
            expected,
            render,
            _canonical_bytes(typed_worker_ledger),
            execution_nonce="e" * 64,
            shard_id=0,
        )

    record, _observation = _consume_worker_response(
        tmp_path,
        control,
        expected,
        render,
        _canonical_bytes(response),
        execution_nonce="e" * 64,
        shard_id=0,
    )
    backend = json.loads(_read_object(tmp_path, record["backend_payload_ref"], ".json"))
    result = json.loads(_read_object(tmp_path, record["result_ref"], ".json"))

    assert backend["raw_provider_payload"] == payload
    assert backend["raw_provider_payload"]["text_word_boxes"][0][0][2] == width + 1
    assert backend["word_box_normalization_ledger"] == ledger
    assert result["word_box_normalization_ledger"] == ledger
    assert (
        result["lines"][0]["words"][0]["normalized_pixel_bbox"]
        == normalized["text_word_boxes"][0][0]
    )
    assert result["words"][0]["normalized_pixel_bbox"] == [width - 10, 10, width, 30]
    assert all(
        "raw_pixel_bbox" not in word for word in [*result["words"], *result["lines"][0]["words"]]
    )
    assert record["word_box_correction_count"] == 1
    assert record["word_box_corrected_edge_count"] == 1


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


@pytest.mark.parametrize("typed_field", ["generation", "accounting"])
def test_checkpoint_replay_rejects_int_to_float_typed_drift(
    project_root: Path,
    tmp_path: Path,
    typed_field: str,
) -> None:
    control = _control_from_sealed(_sealed(project_root))
    expected = next(iter(_control_index(control).values()))
    render = _synthetic_render(tmp_path)
    record = _synthetic_result_fixture(tmp_path, control, expected, render)
    checkpoint = _checkpoint_payload(
        control,
        expected["document_id"],
        [record],
        None,
    )
    if typed_field == "generation":
        checkpoint["generation"] = 1.0
    else:
        checkpoint["accounting"]["completed_request_count"] = 1.0
    payload = _canonical_bytes(checkpoint)
    digest = hashlib.sha256(payload).hexdigest()
    directory = tmp_path / OUTPUT_RELATIVE_ROOT / "checkpoints" / expected["source_sha256"]
    directory.mkdir(parents=True)
    path = directory / f"0001-{digest}.json"
    path.write_bytes(payload)
    path.chmod(0o444)

    with pytest.raises(WaveOneRoleBSentinelError, match="checkpoint generation identity"):
        _load_document_checkpoint(
            tmp_path,
            control,
            expected["document_id"],
            {expected["request_sha256"]: render},
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
    text_tampered_result = deepcopy(result)
    text_tampered_result["lines"][0]["raw_text"] = "fabricated-same-count"
    tampered_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(text_tampered_result),
        suffix=".json",
    )
    tampered = {**record, "result_ref": tampered_result_ref}
    with pytest.raises(WaveOneRoleBSentinelError, match="projection"):
        _validate_result_record(tmp_path, control, tampered, expected, render)

    mislabeled_result = deepcopy(result)
    for word in [
        *mislabeled_result["words"],
        *(word for line in mislabeled_result["lines"] for word in line["words"]),
    ]:
        word["raw_pixel_bbox"] = word.pop("normalized_pixel_bbox")
    mislabeled_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(mislabeled_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="projection"):
        _validate_result_record(
            tmp_path,
            control,
            {**record, "result_ref": mislabeled_result_ref},
            expected,
            render,
        )

    float_bbox_result = deepcopy(result)
    for word in [
        *float_bbox_result["words"],
        *(word for line in float_bbox_result["lines"] for word in line["words"]),
    ]:
        word["normalized_pixel_bbox"][0] = float(word["normalized_pixel_bbox"][0])
    float_bbox_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(float_bbox_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="projection"):
        _validate_result_record(
            tmp_path,
            control,
            {**record, "result_ref": float_bbox_result_ref},
            expected,
            render,
        )

    original_backend = _json_object(
        _read_object(tmp_path, record["backend_payload_ref"], ".json"),
        "fixture backend",
    )
    backend = deepcopy(original_backend)
    backend["bank"] = "forbidden-metadata"
    tampered_backend_ref = _put_object(tmp_path, _canonical_bytes(backend), suffix=".json")
    tampered = {**record, "backend_payload_ref": tampered_backend_ref}
    with pytest.raises(WaveOneRoleBSentinelError, match="identity|embedded"):
        _validate_result_record(tmp_path, control, tampered, expected, render)

    ledger_tampered_result = deepcopy(result)
    ledger_tampered_result["word_box_normalization_ledger"]["normalized_payload_sha256"] = "0" * 64
    ledger_tampered_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(ledger_tampered_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="normalization ledger"):
        _validate_result_record(
            tmp_path,
            control,
            {**record, "result_ref": ledger_tampered_result_ref},
            expected,
            render,
        )

    typed_ref_backend = deepcopy(original_backend)
    typed_ref_backend["render_ref"]["size_bytes"] = float(
        typed_ref_backend["render_ref"]["size_bytes"]
    )
    typed_ref_backend_ref = _put_object(
        tmp_path,
        _canonical_bytes(typed_ref_backend),
        suffix=".json",
    )
    typed_ref_linked_result = deepcopy(result)
    typed_ref_linked_result["backend_payload_ref"] = typed_ref_backend_ref
    typed_ref_linked_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(typed_ref_linked_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="embedded identity"):
        _validate_result_record(
            tmp_path,
            control,
            {
                **record,
                "backend_payload_ref": typed_ref_backend_ref,
                "result_ref": typed_ref_linked_result_ref,
            },
            expected,
            render,
        )

    for field in ("input_render_ref", "backend_payload_ref"):
        typed_ref_result = deepcopy(result)
        typed_ref_result[field]["size_bytes"] = float(typed_ref_result[field]["size_bytes"])
        typed_ref_result_ref = _put_object(
            tmp_path,
            _canonical_bytes(typed_ref_result),
            suffix=".json",
        )
        with pytest.raises(WaveOneRoleBSentinelError, match="embedded identity"):
            _validate_result_record(
                tmp_path,
                control,
                {**record, "result_ref": typed_ref_result_ref},
                expected,
                render,
            )

    typed_safety_result = deepcopy(result)
    typed_safety_result["safety"]["absence_claimed"] = 0
    typed_safety_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(typed_safety_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="embedded identity"):
        _validate_result_record(
            tmp_path,
            control,
            {**record, "result_ref": typed_safety_result_ref},
            expected,
            render,
        )

    typed_ledger_result = deepcopy(result)
    typed_ledger_result["word_box_normalization_ledger"]["correction_count"] = float(
        typed_ledger_result["word_box_normalization_ledger"]["correction_count"]
    )
    typed_ledger_result_ref = _put_object(
        tmp_path,
        _canonical_bytes(typed_ledger_result),
        suffix=".json",
    )
    with pytest.raises(WaveOneRoleBSentinelError, match="normalization ledger"):
        _validate_result_record(
            tmp_path,
            control,
            {**record, "result_ref": typed_ledger_result_ref},
            expected,
            render,
        )

    ledger_tampered_backend = deepcopy(original_backend)
    ledger_tampered_backend["word_box_normalization_ledger"]["raw_payload_sha256"] = "0" * 64
    ledger_tampered_backend_ref = _put_object(
        tmp_path,
        _canonical_bytes(ledger_tampered_backend),
        suffix=".json",
    )
    linked_result = deepcopy(result)
    linked_result["backend_payload_ref"] = ledger_tampered_backend_ref
    linked_result_ref = _put_object(tmp_path, _canonical_bytes(linked_result), suffix=".json")
    with pytest.raises(WaveOneRoleBSentinelError, match="normalization ledger"):
        _validate_result_record(
            tmp_path,
            control,
            {
                **record,
                "backend_payload_ref": ledger_tampered_backend_ref,
                "result_ref": linked_result_ref,
            },
            expected,
            render,
        )


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


def test_worker_predicts_suffix_bearing_lexical_png_and_rehashes_same_inode(
    project_root: Path,
    tmp_path: Path,
) -> None:
    worker = _load_worker(project_root)
    request_sha256 = "a" * 64
    image = tmp_path / f"{request_sha256}.png"
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

    descriptor, image_identity = worker._open_image_fd(
        image,
        hashlib.sha256(b"held-render").hexdigest(),
        len(b"held-render"),
    )
    try:
        payload, normalization_ledger, _elapsed = worker._predict_from_held_render(
            Session(),
            descriptor,
            image,
            pixel_width=200,
            pixel_height=200,
            normalization_authority=_normalization_authority(_normalization_control()),
        )
        worker._revalidate_held_render(
            descriptor,
            image,
            image_identity,
            expected_sha256=hashlib.sha256(b"held-render").hexdigest(),
            expected_size=len(b"held-render"),
        )
    finally:
        os.close(descriptor)
    assert observed == {"path": image.as_posix(), "bytes": b"held-render"}
    assert payload["rec_texts"] == ["Ngân hàng nguồn"]
    assert normalization_ledger["status"] == "NO_CHANGE"


def test_worker_rejects_persistent_private_png_name_swap_and_byte_drift(
    project_root: Path,
    tmp_path: Path,
) -> None:
    worker = _load_worker(project_root)
    expected = b"held-render"
    digest = hashlib.sha256(expected).hexdigest()

    swapped = tmp_path / f"{'b' * 64}.png"
    swapped.write_bytes(expected)
    swapped.chmod(0o444)
    descriptor, identity = worker._open_image_fd(swapped, digest, len(expected))
    try:
        original = tmp_path / "original-private-input.png"
        swapped.rename(original)
        swapped.write_bytes(expected)
        swapped.chmod(0o444)
        with pytest.raises(worker.SentinelWorkerError, match="identity drifted"):
            worker._revalidate_held_render(
                descriptor,
                swapped,
                identity,
                expected_sha256=digest,
                expected_size=len(expected),
            )
    finally:
        os.close(descriptor)

    drifted = tmp_path / f"{'c' * 64}.png"
    drifted.write_bytes(expected)
    drifted.chmod(0o444)
    descriptor, identity = worker._open_image_fd(drifted, digest, len(expected))
    try:
        drifted.chmod(0o644)
        drifted.write_bytes(b"byte-drift!")
        drifted.chmod(0o444)
        with pytest.raises(worker.SentinelWorkerError, match="identity drifted"):
            worker._revalidate_held_render(
                descriptor,
                drifted,
                identity,
                expected_sha256=digest,
                expected_size=len(expected),
            )
    finally:
        os.close(descriptor)


def test_parent_materializes_distinct_immutable_private_png_without_linking_evidence(
    project_root: Path,
    tmp_path: Path,
) -> None:
    render = _synthetic_render(tmp_path)
    request_sha256 = "d" * 64
    request = {"sentinel_ordinal": 1, "request_sha256": request_sha256}
    source = tmp_path / OUTPUT_RELATIVE_ROOT / render["ref"]["path"]
    source_before = source.stat(follow_symlinks=False)
    runtime_root = _create_runtime_root(tmp_path, "e" * 64)
    private = _materialize_private_shard_inputs(
        tmp_path,
        runtime_root.relative_to(tmp_path),
        0,
        [request],
        {request_sha256: render},
        _load_policy(project_root),
    )[request_sha256]
    private_path = Path(private["path"])
    private_identity = private_path.stat(follow_symlinks=False)
    source_after = source.stat(follow_symlinks=False)

    assert private_path.name == f"{request_sha256}.png"
    assert private_path.read_bytes() == render["payload"]
    assert private == {
        "path": private_path.as_posix(),
        "sha256": render["ref"]["sha256"],
        "size_bytes": render["ref"]["size_bytes"],
    }
    assert stat.S_IMODE(private_identity.st_mode) == 0o444
    assert private_identity.st_nlink == 1
    assert (private_identity.st_dev, private_identity.st_ino) != (
        source_before.st_dev,
        source_before.st_ino,
    )
    assert source_after.st_nlink == 1
    assert stat.S_IMODE(source_after.st_mode) == 0o444
    assert (source_after.st_dev, source_after.st_ino, source_after.st_size) == (
        source_before.st_dev,
        source_before.st_ino,
        source_before.st_size,
    )


def test_supervisor_and_worker_reject_private_png_outside_exact_shard_runtime(
    project_root: Path,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import bctc_ai.corpus.wave1_role_b_sentinel as sentinel

    worker = _load_worker(project_root)
    execution_nonce = "f" * 64
    request_sha256 = "1" * 64
    render = _synthetic_render(tmp_path)
    runtime_root = _create_runtime_root(tmp_path, execution_nonce)
    private = _materialize_private_shard_inputs(
        tmp_path,
        runtime_root.relative_to(tmp_path),
        0,
        [{"sentinel_ordinal": 1, "request_sha256": request_sha256}],
        {request_sha256: render},
        _load_policy(project_root),
    )
    monkeypatch.setattr(sentinel, "_worker_model_contract", lambda *_args: ({}, []))
    sealed = {"ppocrv6_runtime_model_ledger": {"sha256": "2" * 64}}
    request = {"sentinel_ordinal": 1, "request_sha256": request_sha256}
    with _execution_lease(tmp_path) as lease_fd:
        task = sentinel._build_worker_task(
            tmp_path,
            tmp_path / "models",
            sealed,
            _normalization_control(),
            0,
            [request],
            {request_sha256: render},
            private,
            execution_nonce,
            {},
            lease_fd,
        )
        assert task["requests"][0]["image_path"] == private[request_sha256]["path"]
        other_shard = deepcopy(private)
        other_shard[request_sha256]["path"] = (
            runtime_root / "shard-1" / "inputs" / f"{request_sha256}.png"
        ).as_posix()
        with pytest.raises(WaveOneRoleBSentinelError, match="task binding"):
            sentinel._build_worker_task(
                tmp_path,
                tmp_path / "models",
                sealed,
                _normalization_control(),
                0,
                [request],
                {request_sha256: render},
                other_shard,
                execution_nonce,
                {},
                lease_fd,
            )

    monkeypatch.setattr(worker, "SENTINEL_RUNTIME_ROOT", tmp_path / "runtime")
    expected_task = tmp_path / "runtime" / f"execution-{execution_nonce}" / "shard-0" / "task.json"
    expected_image = expected_task.parent / "inputs" / f"{request_sha256}.png"
    assert (
        worker._validate_private_input_path(
            expected_task,
            execution_nonce,
            0,
            request_sha256,
            expected_image.as_posix(),
        )
        == expected_image
    )
    with pytest.raises(worker.SentinelWorkerError, match="runtime binding"):
        worker._validate_private_input_path(
            expected_task,
            execution_nonce,
            0,
            request_sha256,
            (tmp_path / "elsewhere" / f"{request_sha256}.png").as_posix(),
        )
    with pytest.raises(worker.SentinelWorkerError, match="runtime binding"):
        worker._validate_private_input_path(
            expected_task,
            execution_nonce,
            1,
            request_sha256,
            expected_image.as_posix(),
        )


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
        "worker": {
            "interpreter": "python.bin",
            "script": "worker.py",
            "provider_input_materialization": "PER_SHARD_PRIVATE_IMMUTABLE_PNG_COPY_V1",
            "provider_input_filename": "REQUEST_SHA256_DOT_PNG",
            "provider_input_mode": "0444",
            "provider_input_hardlink_to_evidence_allowed": False,
        },
    }
    shared_render = _synthetic_render(tmp_path)
    renders = {request["request_sha256"]: shared_render for request in requests}
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
        _control,
        shard_id,
        shard_requests,
        _renders,
        private_inputs,
        _nonce,
        _environment,
        _execution_lease_fd,
    ):
        tasks[shard_id] = [
            {
                **request,
                "image_path": private_inputs[request["request_sha256"]]["path"],
            }
            for request in shard_requests
        ]
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
    assert all(
        Path(request["image_path"]).name == f"{request['request_sha256']}.png"
        for shard_tasks in tasks.values()
        for request in shard_tasks
    )
    assert all(
        Path(request["image_path"]).parent.name == "inputs"
        for shard_tasks in tasks.values()
        for request in shard_tasks
    )
    source = tmp_path / OUTPUT_RELATIVE_ROOT / shared_render["ref"]["path"]
    assert source.stat().st_nlink == 1
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
    control["word_box_normalization"]["normalization_producer_implementation_ledger_sha256"] = (
        "3" * 64
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
                "word_box_correction_count": int(expected["sentinel_ordinal"] == 2),
                "word_box_corrected_edge_count": int(expected["sentinel_ordinal"] == 2),
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
    assert first["word_box_normalization_accounting"] == {
        "corrected_page_count": 1,
        "no_change_page_count": 23,
        "corrected_word_box_count": 1,
        "corrected_edge_count": 1,
        "counts_are_extraction_success_metrics": False,
    }
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
