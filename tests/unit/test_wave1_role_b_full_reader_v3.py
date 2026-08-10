from __future__ import annotations

import ast
import fcntl
import json
import os
import socket
import stat
import subprocess
import sys
from collections import Counter
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
from importlib.metadata import version as distribution_version
from pathlib import Path

import pytest

from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ARCHIVE_ROOT = PROJECT_ROOT / full.FAILED_V2_ARCHIVE_RELATIVE_ROOT


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def _synthetic_raw() -> dict:
    return {
        "dt_polys": [[[0, 0], [100, 0], [100, 20], [0, 20]]],
        "model_settings": {"model_name": "sealed"},
        "page_index": 0,
        "rec_boxes": [[0, 0, 100, 20]],
        "rec_polys": [[[0, 0], [100, 0], [100, 20], [0, 20]]],
        "rec_scores": [0.9],
        "rec_texts": ["10"],
        "return_word_box": True,
        "text_det_params": {"limit_side_len": 64},
        "text_rec_score_thresh": 0.0,
        "text_type": "general",
        "text_word": [["10"]],
        "text_word_boxes": [[[101, 0, 110, 20]]],
        "textline_orientation_angles": [0],
    }


def _make_output_root(project_root: Path) -> Path:
    root = project_root / full.OUTPUT_RELATIVE_ROOT
    root.mkdir(parents=True)
    return root


def _make_output_parent(project_root: Path) -> Path:
    parent = project_root / full.OUTPUT_RELATIVE_ROOT.parent
    parent.mkdir(parents=True)
    return parent


def _temp_names(filename: str, nonce: str = "a" * 32) -> tuple[str, str]:
    return filename, f".{filename}.{nonce}.tmp"


def _publish_temp(
    directory: Path,
    filename: str,
    payload: bytes,
    *,
    mode: int,
    linked: bool,
) -> tuple[Path, Path]:
    final_name, temporary_name = _temp_names(filename)
    temporary = directory / temporary_name
    temporary.write_bytes(payload)
    temporary.chmod(mode)
    final = directory / final_name
    if linked:
        os.link(temporary, final)
    return final, temporary


def _tree_tokens(root: Path) -> list[tuple]:
    if not root.exists():
        return []
    tokens = []
    for path in sorted(root.rglob("*"), key=lambda item: item.relative_to(root).as_posix()):
        identity = os.stat(path, follow_symlinks=False)
        relative = path.relative_to(root).as_posix()
        if stat.S_ISDIR(identity.st_mode):
            tokens.append(
                (
                    "d",
                    relative,
                    identity.st_dev,
                    identity.st_ino,
                    identity.st_mode,
                    identity.st_nlink,
                )
            )
        elif stat.S_ISREG(identity.st_mode):
            tokens.append(
                (
                    "f",
                    relative,
                    identity.st_dev,
                    identity.st_ino,
                    identity.st_mode,
                    identity.st_nlink,
                    identity.st_size,
                    sha256(path.read_bytes()).hexdigest(),
                )
            )
        else:
            tokens.append(("x", relative, identity.st_mode))
    return tokens


def _document_ids() -> list[str]:
    plan = json.loads((PROJECT_ROOT / full.SEALED_PLAN_RELATIVE_PATH).read_bytes())
    return sorted(item["document_id"] for item in plan["documents"])


def _make_complete_output_lock_tree(project_root: Path) -> Path:
    root = _make_output_root(project_root)
    locks = root / "locks"
    documents = locks / "documents"
    documents.mkdir(parents=True)
    (locks / "full-reader-execution.lease").touch(mode=0o600)
    for document_id in _document_ids():
        (documents / f"{document_id.removeprefix('sha256:')}.lock").touch(mode=0o600)
    for name in ("objects", "checkpoints", "documents"):
        (root / name).mkdir()
    control = root / "full-reader-execution-control.json"
    control.write_bytes(b"{}\n")
    control.chmod(0o444)
    return root


def test_policy_and_frozen_native_v2_identities_are_exact() -> None:
    policy = full._v3_load_policy(PROJECT_ROOT)
    native = policy["native_reader"]
    assert native["evidence_adapter_sha256"] == (
        "cc7a8fdf8c8e1332848b5c2583b8b2d4e0fa02e7a60567f2ac464c2ac35e5023"
    )
    assert native["evidence_adapter_size_bytes"] == 71_590
    assert native["native_ordering_policy_identity"] == {
        "path": "config/ocr/causal-native-text-evidence-v2.yaml",
        "sha256": "ec249629e83944f03d25b30d5df29ddfbcd9bc250b06d3ed9cc6d60e2533c309",
        "size_bytes": 1_305,
    }
    assert policy["execution"]["timing_observation_enabled"] is False
    assert "runtime_directory" not in policy["output"]
    assert "upstream_directory" not in policy["output"]


@pytest.mark.parametrize(
    ("section", "key", "value"),
    [
        ("native_reader", "archived_native_checkpoint_adoption_allowed", 0),
        ("native_reader", "request_count", 93.0),
        ("execution", "ocr_worker_allowed", 0),
        ("execution", "minimum_free_space_bytes", 53_687_091_200.0),
        ("safety", "role_a_inputs_allowed", 0),
        ("safety", "failed_v2_archive_mutation_allowed", 0),
    ],
)
def test_policy_typed_drift_rejects(
    monkeypatch: pytest.MonkeyPatch, section: str, key: str, value: object
) -> None:
    policy_path = PROJECT_ROOT / full.POLICY_RELATIVE_PATH
    policy = __import__("yaml").safe_load(policy_path.read_bytes())
    policy[section][key] = value
    drifted = __import__("yaml").safe_dump(policy, sort_keys=False).encode()
    original_stable = full._stable_bytes

    def stable(path: Path, label: str) -> bytes:
        if path == policy_path:
            return drifted
        return original_stable(path, label)

    monkeypatch.setattr(full, "_stable_bytes", stable)
    monkeypatch.setattr(full, "POLICY_SHA256", sha256(drifted).hexdigest())
    monkeypatch.setattr(full, "POLICY_SIZE_BYTES", len(drifted))
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="policy authority"):
        full._v3_load_policy(PROJECT_ROOT)


def test_implementation_ledger_closes_native_v1_v2_and_excludes_full_reader_ancestors() -> None:
    paths = {item.as_posix() for item in full.V3_IMPLEMENTATION_RELATIVE_PATHS}
    assert "src/bctc_ai/ocr/causal_native_text_evidence_v1.py" in paths
    assert "src/bctc_ai/ocr/causal_native_text_evidence_v2.py" in paths
    assert "config/corpus/bank-corpus-wave-1-role-b-sentinel-v1.yaml" in paths
    assert "src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py" in paths
    assert not any(
        name in paths
        for name in {
            "src/bctc_ai/corpus/wave1_role_b_full_reader.py",
            "src/bctc_ai/corpus/wave1_role_b_full_reader_v2.py",
            "scripts/corpus/run_wave1_role_b_full_reader.py",
            "scripts/corpus/run_wave1_role_b_full_reader_v2.py",
            "scripts/models/run_ppocrv6_wave1_full_worker.py",
            "scripts/models/run_ppocrv6_wave1_full_worker_v2.py",
        }
    )


def test_recursive_project_import_closure_is_exactly_ledger_bound() -> None:
    starts = {
        Path("src/bctc_ai/corpus/wave1_role_b_full_reader_v3.py"),
        Path("scripts/corpus/run_wave1_role_b_full_reader_v3.py"),
    }

    def module_name(path: Path) -> str | None:
        if path.parts[:1] != ("src",):
            return None
        parts = list(path.with_suffix("").parts[1:])
        if parts[-1] == "__init__":
            parts.pop()
        return ".".join(parts)

    def resolve(name: str) -> Path | None:
        candidate = Path("src").joinpath(*name.split("."))
        module = candidate.with_suffix(".py")
        package = candidate / "__init__.py"
        if (PROJECT_ROOT / module).is_file():
            return module
        if (PROJECT_ROOT / package).is_file():
            return package
        return None

    closure: set[Path] = set()
    pending = list(starts)
    while pending:
        relative = pending.pop()
        if relative in closure:
            continue
        closure.add(relative)
        tree = ast.parse((PROJECT_ROOT / relative).read_text())
        current = module_name(relative)
        package = (
            current
            if relative.name == "__init__.py"
            else (current.rsplit(".", 1)[0] if current and "." in current else current)
        )
        for node in ast.walk(tree):
            imported: list[str] = []
            if isinstance(node, ast.Import):
                imported.extend(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.level:
                    package_parts = package.split(".") if package else []
                    base_parts = package_parts[: len(package_parts) - node.level + 1]
                    if node.module:
                        base_parts.extend(node.module.split("."))
                    base = ".".join(base_parts)
                else:
                    base = node.module or ""
                imported.append(base)
                imported.extend(f"{base}.{alias.name}" for alias in node.names if alias.name != "*")
            for name in imported:
                if not name.startswith("bctc_ai"):
                    continue
                resolved = resolve(name)
                if resolved is not None and resolved not in closure:
                    pending.append(resolved)

    ledger_python = {path for path in full.V3_IMPLEMENTATION_RELATIVE_PATHS if path.suffix == ".py"}
    allowed_dynamic_extras = {
        Path("src/bctc_ai/__init__.py"),
        Path("src/bctc_ai/core/__init__.py"),
        Path("src/bctc_ai/ocr/__init__.py"),
        Path("src/bctc_ai/rendering/__init__.py"),
        Path("src/bctc_ai/storage/__init__.py"),
        Path("src/bctc_ai/storage/content_store.py"),
        Path("scripts/corpus/run_wave1_role_b_page_reader.py"),
    }
    assert closure <= ledger_python
    assert ledger_python - closure == allowed_dynamic_extras


def test_module_has_no_ocr_worker_or_forbidden_metadata_execution_surface() -> None:
    source = Path(full.__file__).read_text()
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imports & {"requests", "httpx", "boto3", "urllib", "aiohttp"}
    assert "run_ppocrv6_wave1_full_worker" not in source
    assert "full-v2-failed" in source  # fixed evidence authority, not an executor import
    assert "role_a_inputs_allowed" in source
    assert "schema_inputs_allowed" in source


def test_typed_json_distinguishes_signed_zero_and_nonfinite() -> None:
    assert full._same_typed_json(0.0, -0.0) is False
    assert full._same_typed_json([0.0], [-0.0]) is False
    assert full._same_typed_json(float("nan"), float("nan")) is False
    assert full._same_typed_json(float("inf"), float("inf")) is False


def test_exact_archived_ppocr_schema_accepts_only_all_fourteen_keys() -> None:
    raw = _synthetic_raw()
    counts = full._validate_ppocrv6_schema_except_word_geometry(
        raw, pixel_width=120, pixel_height=40
    )
    assert counts == {"line_count": 1, "word_token_count": 1}
    for key in tuple(raw):
        drifted = deepcopy(raw)
        drifted.pop(key)
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="field set"):
            full._validate_ppocrv6_schema_except_word_geometry(
                drifted, pixel_width=120, pixel_height=40
            )
    drifted = {**raw, "foreign": None}
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="field set"):
        full._validate_ppocrv6_schema_except_word_geometry(
            drifted, pixel_width=120, pixel_height=40
        )


def test_all_real_archived_terminal_raw_payloads_pass_exact_nonword_gate() -> None:
    count = 0
    for checkpoint_path in sorted((ARCHIVE_ROOT / "checkpoints").glob("*/*.json")):
        record = json.loads(checkpoint_path.read_bytes())["page_record"]
        if record["status"] != "UNRESOLVED_OCR_WORD_BOX_GEOMETRY":
            continue
        backend = json.loads((ARCHIVE_ROOT / record["backend_payload_ref"]["path"]).read_bytes())
        result = json.loads((ARCHIVE_ROOT / record["result_ref"]["path"]).read_bytes())
        width, height = result["coordinate_authority"]["pixel_dimensions"]
        full._validate_ppocrv6_schema_except_word_geometry(
            backend["raw_provider_payload"],
            pixel_width=width,
            pixel_height=height,
        )
        count += 1
    assert count == 57


def test_historical_v2_safety_projection_is_exact() -> None:
    assert full._v2_result_safety() == {
        "absence_claimed": False,
        "bank_registry_metadata_used": False,
        "cells_interpreted": False,
        "filename_metadata_used": False,
        "historical_values_used": False,
        "mapping_used": False,
        "role_a_used": False,
        "rows_reconstructed": False,
        "schema_used": False,
        "statement_classified": False,
        "table_classified": False,
    }


def test_network_denial_blocks_and_restores_every_hook() -> None:
    originals = (
        socket.create_connection,
        socket.getaddrinfo,
        socket.socket.connect,
        socket.socket.connect_ex,
    )
    with full._v3_network_denied():
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="network access"):
            socket.create_connection(("127.0.0.1", 1))
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="network access"):
            socket.getaddrinfo("localhost", 1)
    assert (
        socket.create_connection,
        socket.getaddrinfo,
        socket.socket.connect,
        socket.socket.connect_ex,
    ) == originals


def test_network_denial_restores_after_body_error_and_hook_replacement() -> None:
    original = socket.create_connection
    with pytest.raises(RuntimeError, match="body"):
        with full._v3_network_denied():
            raise RuntimeError("body")
    assert socket.create_connection is original
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="guard was replaced"):
        with full._v3_network_denied():
            socket.create_connection = original
    assert socket.create_connection is original


@pytest.mark.parametrize(
    ("process_umask", "expected"), [("0022", "PASS"), ("0027", "REJECT"), ("0077", "REJECT")]
)
def test_mutating_entry_requires_exact_process_umask_in_subprocess(
    tmp_path: Path, process_umask: str, expected: str
) -> None:
    marker = tmp_path / "entered"
    script = """
import os
import pathlib
import sys
from bctc_ai.corpus import wave1_role_b_full_reader_v3 as full
os.umask(int(sys.argv[1], 8))
try:
    with full._v3_mutation_entry():
        pathlib.Path(sys.argv[2]).write_text('entered')
except full.WaveOneRoleBFullReaderError:
    print('REJECT')
else:
    print('PASS')
"""
    result = subprocess.run(
        [sys.executable, "-c", script, process_umask, str(marker)],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
    )
    assert result.stdout.strip() == expected
    assert marker.exists() is (expected == "PASS")


def test_independent_v3_cas_first_publish_idempotence_and_root_isolation(
    tmp_path: Path,
) -> None:
    payload = b'{"v3":"exact"}\n'
    reference = full._put_object(tmp_path, payload, suffix=".json")
    path = tmp_path / full.OUTPUT_RELATIVE_ROOT / reference["path"]
    first = os.stat(path, follow_symlinks=False)
    assert stat.S_IMODE(first.st_mode) == 0o444
    assert first.st_nlink == 1
    assert path.read_bytes() == payload
    replay = full._put_object(tmp_path, payload, suffix=".json")
    second = os.stat(path, follow_symlinks=False)
    assert replay == reference
    assert (first.st_dev, first.st_ino, first.st_mtime_ns) == (
        second.st_dev,
        second.st_ino,
        second.st_mtime_ns,
    )
    sentinel_root = tmp_path / full.sentinel.OUTPUT_RELATIVE_ROOT
    assert not sentinel_root.exists()


@pytest.mark.parametrize(("mode", "linked"), [(0o600, False), (0o444, False), (0o444, True)])
def test_publication_recovery_covers_partial_immutable_and_linked_phases(
    tmp_path: Path, mode: int, linked: bool
) -> None:
    directory = _make_output_root(tmp_path) / "documents"
    directory.mkdir()
    filename = f"{'a' * 64}.json"
    payload = b'{"exact":true}\n'
    final, temporary = _publish_temp(directory, filename, payload, mode=mode, linked=linked)
    full._v3_recover_publication_directory(
        tmp_path,
        full.OUTPUT_RELATIVE_ROOT / "documents",
        create=False,
        allowed_final=lambda candidate: candidate == filename,
        validate_payload=lambda candidate, observed: candidate == filename and observed == payload,
    )
    assert not temporary.exists()
    if linked:
        identity = os.stat(final, follow_symlinks=False)
        assert identity.st_nlink == 1
        assert stat.S_IMODE(identity.st_mode) == 0o444
        assert final.read_bytes() == payload
    else:
        assert not final.exists()


def test_publication_recovery_rejects_multiple_or_conflicting_without_mutation(
    tmp_path: Path,
) -> None:
    directory = _make_output_root(tmp_path) / "documents"
    directory.mkdir()
    payload = b'{"exact":true}\n'
    for suffix in ("a" * 64, "b" * 64):
        _publish_temp(directory, f"{suffix}.json", payload, mode=0o444, linked=False)
    before = _tree_tokens(directory)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="multiple"):
        full._v3_recover_publication_directory(
            tmp_path,
            full.OUTPUT_RELATIVE_ROOT / "documents",
            create=False,
            allowed_final=lambda _candidate: True,
            validate_payload=lambda _candidate, _payload: True,
        )
    assert _tree_tokens(directory) == before


@pytest.mark.parametrize("linked", [False, True])
def test_checkpoint_recovery_exits_bound_snapshot_then_reloads_fresh(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    linked: bool,
) -> None:
    document_id = f"sha256:{'d' * 64}"
    request_sha = "a" * 64
    control = {"control_identity_sha256": "c" * 64}
    record = {"request_sha256": request_sha}
    checkpoint = full._v3_checkpoint_payload(control, document_id, record, 1, None)
    payload = _canonical(checkpoint)
    digest = sha256(payload).hexdigest()
    filename = f"0001-{digest}.json"
    directory = _make_output_root(tmp_path) / "checkpoints" / document_id.removeprefix("sha256:")
    directory.mkdir(parents=True)
    final, temporary = _publish_temp(
        directory,
        filename,
        payload,
        mode=(0o444 if linked else 0o600),
        linked=linked,
    )
    monkeypatch.setattr(full, "_v3_control_index", lambda _control: {request_sha: {}})
    monkeypatch.setattr(
        full, "_v3_document_completion_order", lambda _control, _document: [request_sha]
    )
    monkeypatch.setattr(full, "_v3_validate_page_record", lambda *_args, **_kwargs: None)
    manifest_before = full._v3_output_live_manifest(tmp_path)
    pair_path = (
        final.relative_to(tmp_path / full.OUTPUT_RELATIVE_ROOT).as_posix() if linked else None
    )
    with full._v3_bind_output_reads(tmp_path, manifest_before):
        observed, observed_head = full._v3_load_document_checkpoints(
            tmp_path,
            control,
            document_id,
            {},
            tmp_path / "archive",
            {},
            recover_temporaries=False,
            publication_pair_path=pair_path,
            observe_temporary=True,
        )
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="cannot mutate a bound"):
            full._v3_recover_publication_directory(
                tmp_path,
                full.OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:"),
                create=False,
                allowed_final=lambda candidate: candidate == filename,
                validate_payload=lambda candidate, value: (
                    candidate == filename and sha256(value).hexdigest() == digest
                ),
                expected_output_manifest=manifest_before,
            )
    full._v3_recover_publication_directory(
        tmp_path,
        full.OUTPUT_RELATIVE_ROOT / "checkpoints" / document_id.removeprefix("sha256:"),
        create=False,
        allowed_final=lambda candidate: candidate == filename,
        validate_payload=lambda candidate, value: (
            candidate == filename and sha256(value).hexdigest() == digest
        ),
        expected_output_manifest=manifest_before,
    )
    assert not temporary.exists()
    manifest_after = full._v3_output_live_manifest(tmp_path)
    with full._v3_bind_output_reads(tmp_path, manifest_after):
        replayed, replayed_head = full._v3_load_document_checkpoints(
            tmp_path,
            control,
            document_id,
            {},
            tmp_path / "archive",
            {},
            recover_temporaries=False,
        )
    assert replayed == observed
    assert replayed_head == observed_head
    assert final.exists() is linked


def test_global_preflight_rejects_foreign_checkpoint_namespace_without_mutation(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    checkpoints = root / "checkpoints"
    checkpoints.mkdir()
    (checkpoints / ("f" * 64)).mkdir()
    before = _tree_tokens(root)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="foreign directory"):
        full._v3_preflight_output_temporaries(tmp_path, _document_ids())
    assert _tree_tokens(root) == before


def test_global_preflight_rejects_symlink_and_multiple_temps_without_mutation(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    documents = root / "documents"
    documents.mkdir()
    os.symlink(tmp_path, documents / "bad")
    before = _tree_tokens(root)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="symlink"):
        full._v3_preflight_output_temporaries(tmp_path, _document_ids())
    assert _tree_tokens(root) == before
    (documents / "bad").unlink()
    expected = _document_ids()[:2]
    for document_id in expected:
        _publish_temp(
            documents,
            f"{document_id.removeprefix('sha256:')}.json",
            b"partial",
            mode=0o600,
            linked=False,
        )
    before = _tree_tokens(root)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="multiple"):
        full._v3_preflight_output_temporaries(tmp_path, _document_ids())
    assert _tree_tokens(root) == before


def test_output_live_manifest_detects_same_name_content_replacement(tmp_path: Path) -> None:
    root = _make_output_root(tmp_path)
    path = root / "control.json"
    path.write_bytes(b"one")
    path.chmod(0o444)
    before = full._v3_output_live_manifest(tmp_path)
    path.unlink()
    path.write_bytes(b"two")
    path.chmod(0o444)
    after = full._v3_output_live_manifest(tmp_path)
    assert not full._same_typed_json(before, after)


def test_bound_output_read_uses_held_parent_and_rejects_swap_restore(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    original = root / "original"
    alternate = root / "alternate"
    original.mkdir()
    alternate.mkdir()
    (original / "value.json").write_bytes(b'"original"\n')
    (alternate / "value.json").write_bytes(b'"alternate"\n')
    (original / "value.json").chmod(0o444)
    (alternate / "value.json").chmod(0o444)
    manifest = full._v3_output_live_manifest(tmp_path)
    detached = root / "detached"
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="bound output directory"):
        with full._v3_bind_output_reads(tmp_path, manifest):
            original.rename(detached)
            alternate.rename(original)
            payload, _identity = full._v3_read_nofollow(
                original / "value.json", "synthetic bound output file"
            )
            assert payload == b'"original"\n'
            original.rename(alternate)
            detached.rename(original)


def test_execution_lease_bootstrap_rolls_back_exact_owned_tree(
    tmp_path: Path,
) -> None:
    _make_output_parent(tmp_path)
    with pytest.raises(RuntimeError, match="synthetic failure"):
        with full._v3_execution_lease(tmp_path, create=True):
            raise RuntimeError("synthetic failure")
    assert not (tmp_path / full.OUTPUT_RELATIVE_ROOT).exists()


@pytest.mark.parametrize(
    "failure_point",
    [
        "root_identity",
        "root_open",
        "root_flock",
        "locks_identity",
        "locks_open",
        "lease_fstat",
        "lease_stat",
        "lease_identity",
    ],
)
def test_execution_lease_setup_failure_rolls_back_owned_prefix_and_fds(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    _make_output_parent(tmp_path)
    baseline_fds = len(os.listdir("/proc/self/fd"))
    original_open = full.os.open
    original_fstat = full.os.fstat
    original_stat = full.os.stat
    original_flock = full.fcntl.flock
    original_lock_identity = full._v3_lock_identity
    triggered = False
    exclusive_acquisitions = 0
    created_lease_descriptor: int | None = None

    def stat_path(path: object, *args: object, **kwargs: object) -> os.stat_result:
        nonlocal triggered
        if (
            not triggered
            and failure_point == "root_identity"
            and path == full.OUTPUT_RELATIVE_ROOT.name
            and kwargs.get("dir_fd") is not None
        ):
            triggered = True
            raise OSError("synthetic root identity failure")
        if (
            not triggered
            and failure_point == "locks_identity"
            and path == "locks"
            and kwargs.get("dir_fd") is not None
        ):
            triggered = True
            raise OSError("synthetic locks identity failure")
        if (
            not triggered
            and failure_point == "lease_stat"
            and path == "full-reader-execution.lease"
            and kwargs.get("dir_fd") is not None
        ):
            triggered = True
            raise OSError("synthetic lease stat failure")
        return original_stat(path, *args, **kwargs)

    def open_file(path: object, *args: object, **kwargs: object) -> int:
        nonlocal created_lease_descriptor, triggered
        if (
            not triggered
            and failure_point == "root_open"
            and path == full.OUTPUT_RELATIVE_ROOT.name
            and kwargs.get("dir_fd") is not None
        ):
            triggered = True
            raise OSError("synthetic root open failure")
        if (
            not triggered
            and failure_point == "locks_open"
            and path == "locks"
            and kwargs.get("dir_fd") is not None
        ):
            triggered = True
            raise OSError("synthetic locks open failure")
        descriptor = original_open(path, *args, **kwargs)
        if path == "full-reader-execution.lease" and kwargs.get("dir_fd") is not None:
            created_lease_descriptor = descriptor
        return descriptor

    def fstat(descriptor: int) -> os.stat_result:
        nonlocal triggered
        if (
            not triggered
            and failure_point == "lease_fstat"
            and descriptor == created_lease_descriptor
        ):
            triggered = True
            raise OSError("synthetic lease fstat failure")
        return original_fstat(descriptor)

    def flock(descriptor: int, operation: int) -> None:
        nonlocal triggered, exclusive_acquisitions
        if operation == fcntl.LOCK_EX | fcntl.LOCK_NB:
            exclusive_acquisitions += 1
            if not triggered and failure_point == "root_flock" and exclusive_acquisitions == 2:
                triggered = True
                raise BlockingIOError("synthetic root flock failure")
        original_flock(descriptor, operation)

    def lock_identity(
        descriptor: int, directory_fd: int, name: str, *, mode: int
    ) -> tuple[int, int]:
        nonlocal triggered
        if (
            not triggered
            and failure_point == "lease_identity"
            and name == "full-reader-execution.lease"
        ):
            triggered = True
            raise full.WaveOneRoleBFullReaderError("synthetic lease identity failure")
        return original_lock_identity(descriptor, directory_fd, name, mode=mode)

    monkeypatch.setattr(full.os, "open", open_file)
    monkeypatch.setattr(full.os, "fstat", fstat)
    monkeypatch.setattr(full.os, "stat", stat_path)
    monkeypatch.setattr(full.fcntl, "flock", flock)
    monkeypatch.setattr(full, "_v3_lock_identity", lock_identity)
    with pytest.raises((OSError, full.WaveOneRoleBFullReaderError)):
        with full._v3_execution_lease(tmp_path, create=True):
            raise AssertionError("unreachable")
    assert triggered is True
    assert not (tmp_path / full.OUTPUT_RELATIVE_ROOT).exists()
    assert len(os.listdir("/proc/self/fd")) == baseline_fds


def test_execution_lease_holds_exclusive_retained_root_lock(tmp_path: Path) -> None:
    _make_output_parent(tmp_path)
    with full._v3_execution_lease(tmp_path, create=True):
        descriptor = os.open(tmp_path / full.OUTPUT_RELATIVE_ROOT, os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)
    assert not (tmp_path / full.OUTPUT_RELATIVE_ROOT).exists()


def test_lock_files_are_fsynced_before_control_or_evidence_body(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_output_parent(tmp_path)
    original_fsync = full.os.fsync
    events: list[tuple[int, int]] = []

    def fsync(descriptor: int) -> None:
        events.append((descriptor, os.fstat(descriptor).st_mode))
        original_fsync(descriptor)

    monkeypatch.setattr(full.os, "fsync", fsync)
    with full._v3_execution_lease(tmp_path, create=True) as lease_fd:
        assert any(descriptor == lease_fd and stat.S_ISREG(mode) for descriptor, mode in events)
        events.clear()
        with full._v3_document_locks(tmp_path, _document_ids()):
            file_positions = [
                index for index, (_descriptor, mode) in enumerate(events) if stat.S_ISREG(mode)
            ]
            directory_positions = [
                index for index, (_descriptor, mode) in enumerate(events) if stat.S_ISDIR(mode)
            ]
            assert len(file_positions) == 27
            assert directory_positions
            assert max(file_positions) < max(directory_positions)
        full._V3_CONTROL_COMMIT_MARKER.set(True)


def test_execution_lease_rejects_independently_held_root_lock(tmp_path: Path) -> None:
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    locks.mkdir()
    (locks / "full-reader-execution.lease").touch(mode=0o600)
    descriptor = os.open(root, os.O_RDONLY)
    fcntl.flock(descriptor, fcntl.LOCK_SH | fcntl.LOCK_NB)
    try:
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="root is already held"):
            with full._v3_execution_lease(tmp_path, create=False):
                raise AssertionError("unreachable")
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def test_read_only_snapshot_holds_shared_retained_root_lock(tmp_path: Path) -> None:
    root = _make_complete_output_lock_tree(tmp_path)
    with full._v3_read_only_output_snapshot(tmp_path, _document_ids()):
        descriptor = os.open(root, os.O_RDONLY)
        try:
            with pytest.raises(BlockingIOError):
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        finally:
            os.close(descriptor)


def test_retained_root_publication_never_writes_transient_replacement(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_output_parent(tmp_path)
    root = tmp_path / full.OUTPUT_RELATIVE_ROOT
    saved = root.with_name("full-v3-saved")
    alternate = root.with_name("full-v3-alternate")
    original_assert = full._v3_assert_output_mutation_ancestry
    swapped = False

    def barrier(project_root: Path, label: str) -> None:
        nonlocal swapped
        if label == "V3 immutable publication completion" and swapped:
            root.rename(alternate)
            saved.rename(root)
        original_assert(project_root, label)
        if label == "V3 immutable publication" and not swapped:
            root.rename(saved)
            root.mkdir()
            swapped = True

    monkeypatch.setattr(full, "_v3_assert_output_mutation_ancestry", barrier)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="bootstrap parent changed"):
        with full._v3_execution_lease(tmp_path, create=True):
            full._publish_exclusive(
                tmp_path,
                full.OUTPUT_RELATIVE_ROOT,
                "full-reader-execution-control.json",
                b'{"exact":true}\n',
            )
            full._V3_CONTROL_COMMIT_MARKER.set(True)
    assert (root / "full-reader-execution-control.json").read_bytes() == b'{"exact":true}\n'
    assert _tree_tokens(alternate) == []


def test_owned_bootstrap_rollback_keeps_lease_locked_until_unlink(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_output_parent(tmp_path)
    original_unlink = os.unlink
    observed_locked = False

    def unlink(name: str, *args: object, **kwargs: object) -> None:
        nonlocal observed_locked
        if name == "full-reader-execution.lease":
            directory_fd = kwargs["dir_fd"]
            assert isinstance(directory_fd, int)
            competitor = os.open(name, os.O_RDWR, dir_fd=directory_fd)
            try:
                with pytest.raises(BlockingIOError):
                    fcntl.flock(competitor, fcntl.LOCK_EX | fcntl.LOCK_NB)
                observed_locked = True
            finally:
                os.close(competitor)
        original_unlink(name, *args, **kwargs)

    monkeypatch.setattr(full.os, "unlink", unlink)
    with pytest.raises(RuntimeError, match="synthetic"):
        with full._v3_execution_lease(tmp_path, create=True):
            raise RuntimeError("synthetic")
    assert observed_locked is True
    assert not (tmp_path / full.OUTPUT_RELATIVE_ROOT).exists()


def test_foreign_control_name_does_not_suppress_owned_bootstrap_rollback(
    tmp_path: Path,
) -> None:
    _make_output_parent(tmp_path)
    with pytest.raises(RuntimeError, match="synthetic"):
        with full._v3_execution_lease(tmp_path, create=True):
            root = tmp_path / full.OUTPUT_RELATIVE_ROOT
            control = root / "full-reader-execution-control.json"
            control.write_bytes(b"foreign\n")
            control.chmod(0o444)
            raise RuntimeError("synthetic")
    root = tmp_path / full.OUTPUT_RELATIVE_ROOT
    assert (root / "full-reader-execution-control.json").read_bytes() == b"foreign\n"
    assert not (root / "locks").exists()


def test_execution_cleanup_continues_after_unlock_and_close_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_output_parent(tmp_path)
    baseline_fds = len(os.listdir("/proc/self/fd"))
    original_flock = full.fcntl.flock
    original_close = full.os.close
    raised_unlock = False
    raised_close = False

    def flock(descriptor: int, operation: int) -> None:
        nonlocal raised_unlock
        original_flock(descriptor, operation)
        if operation == fcntl.LOCK_UN and not raised_unlock:
            raised_unlock = True
            raise OSError("synthetic unlock cleanup failure")

    def close(descriptor: int) -> None:
        nonlocal raised_close
        original_close(descriptor)
        if not raised_close:
            raised_close = True
            raise OSError("synthetic close cleanup failure")

    monkeypatch.setattr(full.fcntl, "flock", flock)
    monkeypatch.setattr(full.os, "close", close)
    with pytest.raises(OSError, match="synthetic unlock cleanup"):
        with full._v3_execution_lease(tmp_path, create=True):
            full._V3_CONTROL_COMMIT_MARKER.set(True)
    assert raised_unlock is True and raised_close is True
    assert full._V3_OUTPUT_MUTATION_BINDING.get() is None
    assert full._V3_CONTROL_COMMIT_MARKER.get() is False
    assert len(os.listdir("/proc/self/fd")) == baseline_fds
    root = tmp_path / full.OUTPUT_RELATIVE_ROOT
    root_fd = os.open(root, os.O_RDONLY)
    lease_fd = os.open(root / "locks" / "full-reader-execution.lease", os.O_RDWR)
    try:
        fcntl.flock(root_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        fcntl.flock(lease_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    finally:
        fcntl.flock(lease_fd, fcntl.LOCK_UN)
        fcntl.flock(root_fd, fcntl.LOCK_UN)
        os.close(lease_fd)
        os.close(root_fd)


def test_control_publication_commit_retains_bootstrap_on_replay_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _make_output_parent(tmp_path)
    documents = [{"document_id": item} for item in _document_ids()]
    policy = {"execution": {"minimum_free_space_bytes": 0}}
    control = {"exact_control": True}
    monkeypatch.setattr(
        full,
        "_v3_authenticate_plan",
        lambda *_args, **_kwargs: ({"documents": documents}, policy, {}),
    )
    monkeypatch.setattr(full, "_v3_failed_archive_locks", lambda *_args, **_kwargs: nullcontext(()))
    monkeypatch.setattr(
        full,
        "_v3_build_authenticated_control_held",
        lambda *_args, **_kwargs: control,
    )
    monkeypatch.setattr(full, "_v3_ensure_capacity", lambda *_args: None)

    def fail_after_publication(_project_root: Path) -> dict:
        raise full.WaveOneRoleBFullReaderError("synthetic replay failure")

    monkeypatch.setattr(full, "_v3_load_published_control", fail_after_publication)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="synthetic replay"):
        full._publish_authenticated_control_mutating(tmp_path, model_cache=tmp_path)
    root = tmp_path / full.OUTPUT_RELATIVE_ROOT
    assert (root / "full-reader-execution-control.json").read_bytes() == _canonical(control)
    assert set(item.name for item in (root / "locks").iterdir()) == {"full-reader-execution.lease"}


def test_archive_and_output_share_one_retained_parent_generation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_ids = _document_ids()
    archive_relative = full.OUTPUT_RELATIVE_ROOT.parent / "synthetic-failed-v2"
    receipt_relative = full.OUTPUT_RELATIVE_ROOT.parent / "synthetic-incident.json"
    archive = tmp_path / archive_relative
    archive_documents = archive / "locks" / "documents"
    archive_documents.mkdir(parents=True)
    (archive / "locks" / "full-reader-execution.lease").touch(mode=0o600)
    for document_id in document_ids:
        (archive_documents / f"{document_id.removeprefix('sha256:')}.lock").touch(mode=0o600)
    receipt = tmp_path / receipt_relative
    receipt.write_bytes(b"{}\n")
    receipt.chmod(0o444)
    monkeypatch.setattr(full, "FAILED_V2_ARCHIVE_RELATIVE_ROOT", archive_relative)
    monkeypatch.setattr(full, "FAILED_V2_RECEIPT_RELATIVE_PATH", receipt_relative)

    with full._v3_failed_archive_locks(tmp_path, document_ids):
        shared_parent = full._V3_SHARED_OUTPUT_PARENT_BINDING.get()
        assert shared_parent is not None
        with full._v3_execution_lease(tmp_path, create=True):
            full._publish_exclusive(
                tmp_path,
                full.OUTPUT_RELATIVE_ROOT,
                "full-reader-execution-control.json",
                b'{"exact":true}\n',
            )
            full._V3_CONTROL_COMMIT_MARKER.set(True)
    output = tmp_path / full.OUTPUT_RELATIVE_ROOT
    assert (output / "full-reader-execution-control.json").read_bytes() == b'{"exact":true}\n'
    assert (archive / "locks" / "full-reader-execution.lease").exists()


@pytest.mark.parametrize(
    "failure_point", ["ancestor_fstat", "archive_open", "locks_open", "documents_open"]
)
def test_archive_generation_open_failures_release_every_fd(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_point: str,
) -> None:
    document_ids = _document_ids()
    archive_relative = full.OUTPUT_RELATIVE_ROOT.parent / "synthetic-failed-v2"
    receipt_relative = full.OUTPUT_RELATIVE_ROOT.parent / "synthetic-incident.json"
    archive = tmp_path / archive_relative
    archive_documents = archive / "locks" / "documents"
    archive_documents.mkdir(parents=True)
    (archive / "locks" / "full-reader-execution.lease").touch(mode=0o600)
    for document_id in document_ids:
        (archive_documents / f"{document_id.removeprefix('sha256:')}.lock").touch(mode=0o600)
    receipt = tmp_path / receipt_relative
    receipt.write_bytes(b"{}\n")
    receipt.chmod(0o444)
    monkeypatch.setattr(full, "FAILED_V2_ARCHIVE_RELATIVE_ROOT", archive_relative)
    monkeypatch.setattr(full, "FAILED_V2_RECEIPT_RELATIVE_PATH", receipt_relative)
    original_open = full.os.open
    original_fstat = full.os.fstat
    triggered = False

    def open_file(path: object, *args: object, **kwargs: object) -> int:
        nonlocal triggered
        target = {
            "archive_open": archive_relative.name,
            "locks_open": "locks",
            "documents_open": "documents",
        }.get(failure_point)
        if not triggered and target is not None and path == target:
            triggered = True
            raise OSError(f"synthetic {failure_point}")
        return original_open(path, *args, **kwargs)

    def fstat(descriptor: int) -> os.stat_result:
        nonlocal triggered
        if not triggered and failure_point == "ancestor_fstat":
            target = Path(os.readlink(f"/proc/self/fd/{descriptor}"))
            if target == tmp_path / "output":
                triggered = True
                raise OSError("synthetic ancestor fstat")
        return original_fstat(descriptor)

    monkeypatch.setattr(full.os, "open", open_file)
    monkeypatch.setattr(full.os, "fstat", fstat)
    baseline_fds = len(os.listdir("/proc/self/fd"))
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        with full._v3_failed_archive_locks(tmp_path, document_ids):
            raise AssertionError("unreachable")
    assert triggered is True
    assert len(os.listdir("/proc/self/fd")) == baseline_fds
    assert full._V3_ARCHIVE_READ_BINDING.get() is None
    assert full._V3_ARCHIVE_RECEIPT_READ_BINDING.get() is None
    assert full._V3_SHARED_OUTPUT_PARENT_BINDING.get() is None


def test_execution_lease_rollback_generation_swap_mutates_neither_tree(
    tmp_path: Path,
) -> None:
    _make_output_parent(tmp_path)
    root = tmp_path / full.OUTPUT_RELATIVE_ROOT
    saved = root.with_name("full-v3-saved")
    replacement = root
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="topology drifted"):
        with full._v3_execution_lease(tmp_path, create=True):
            before_original = _tree_tokens(root)
            root.rename(saved)
            replacement.mkdir()
            before_replacement = _tree_tokens(replacement)
            raise RuntimeError("body failure after root replacement")
    assert _tree_tokens(saved) == before_original
    assert _tree_tokens(replacement) == before_replacement


def test_execution_lease_rejects_active_locks_generation_swap(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    locks.mkdir()
    (locks / "full-reader-execution.lease").touch(mode=0o600)
    saved = root / "locks-saved"
    with full._v3_execution_lease(tmp_path, create=False):
        locks.rename(saved)
        locks.mkdir()
        (locks / "full-reader-execution.lease").touch(mode=0o600)
        try:
            with pytest.raises(full.WaveOneRoleBFullReaderError, match="ancestry generation"):
                full._v3_preflight_output_temporaries(tmp_path, _document_ids(), stage="run")
        finally:
            (locks / "full-reader-execution.lease").unlink()
            locks.rmdir()
            saved.rename(locks)


def test_missing_control_rejects_later_phase_tree_without_mutation(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    locks.mkdir()
    (locks / "full-reader-execution.lease").touch(mode=0o600)
    (root / "objects").mkdir()
    before = _tree_tokens(root)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="exact bootstrap"):
        full._v3_preflight_output_temporaries(tmp_path, _document_ids(), stage="control")
    assert _tree_tokens(root) == before


def test_control_only_lock_state_rejects_later_artifact_without_mutation(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    locks.mkdir()
    (locks / "full-reader-execution.lease").touch(mode=0o600)
    control = root / "full-reader-execution-control.json"
    control.write_bytes(b"{}\n")
    control.chmod(0o444)
    (root / "objects").mkdir()
    before = _tree_tokens(root)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="evidence phase"):
        full._v3_output_lock_state(tmp_path, _document_ids())
    assert _tree_tokens(root) == before


def test_completed_checkpoint_phase_rejects_empty_cas_prefix_without_mutation(
    tmp_path: Path,
) -> None:
    root = _make_output_root(tmp_path)
    checkpoints = root / "checkpoints"
    checkpoints.mkdir()
    document_ids = _document_ids()
    created = 0
    for index, document_id in enumerate(document_ids):
        directory = checkpoints / document_id.removeprefix("sha256:")
        directory.mkdir()
        count = 54 if index < 18 else 53
        for generation in range(1, count + 1):
            path = directory / f"{generation:04d}-{'a' * 64}.json"
            path.touch()
            path.chmod(0o444)
            created += 1
    assert created == 1_449
    (root / "objects" / "sha256" / "aa").mkdir(parents=True)
    before = full._v3_output_live_manifest(tmp_path)
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="completion phase"):
        full._v3_preflight_output_temporaries(tmp_path, document_ids, stage="run")
    after = full._v3_output_live_manifest(tmp_path)
    assert full._same_typed_json(after, before)


def test_read_only_snapshot_rejects_exclusive_lease_contention(tmp_path: Path) -> None:
    document_ids = _document_ids()
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    documents = locks / "documents"
    documents.mkdir(parents=True)
    lease = locks / "full-reader-execution.lease"
    lease.touch(mode=0o600)
    for document_id in document_ids:
        (documents / f"{document_id.removeprefix('sha256:')}.lock").touch(mode=0o600)
    descriptor = os.open(lease, os.O_RDWR)
    fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="active mutating"):
            with full._v3_read_only_output_snapshot(tmp_path, document_ids):
                raise AssertionError("unreachable")
    finally:
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        os.close(descriptor)


def test_cli_reports_authenticated_publication_state_without_unlocked_exists_probe() -> None:
    source = (PROJECT_ROOT / "scripts/corpus/run_wave1_role_b_full_reader_v3.py").read_text()
    assert '"published": False' not in source
    assert '"published": True' not in source
    assert "authenticated_published_aggregate_present" in source
    assert ".exists()" not in source


def test_aggregate_vocabulary_and_exact_fixed_partitions_are_present() -> None:
    source = Path(full.__file__).read_text()
    for token in (
        '"BANK_CORPUS_WAVE_1_ROLE_B_PAGE_READS_V2"',
        '"200": ocr_dpi[200]',
        '"300": ocr_dpi[300]',
        '"AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY": 24',
        '"PINNED_PPOCRV6_FULL_READER": 1_332',
        '"noncontiguous_line_identity_count"',
    ):
        assert token in source


def test_executable_aggregate_projection_closes_all_fixed_partitions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    document_ids = [f"sha256:{index + 10_000:064x}" for index in range(27)]
    records: list[dict] = []
    for index in range(1_356):
        complete = index < 1_299
        records.append(
            {
                "request_ordinal": index + 1,
                "request_sha256": f"{index + 1:064x}",
                "document_id": document_ids[index % 27],
                "route": full._OCR_ROUTE,
                "status": (
                    "OCR_WORD_BOX_READ_COMPLETE" if complete else "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
                ),
                "origin": "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY",
                "upstream_origin": (
                    "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY"
                    if index < 24
                    else "PINNED_PPOCRV6_FULL_READER"
                ),
                "request": {"render_specification": {"dpi": 200 if index < 1_250 else 300}},
                "line_axis_count": 96_369 if index == 0 else 0,
                "nonempty_line_axis_count": 96_304 if index == 0 else 0,
                "exact_empty_line_axis_count": 65 if index == 0 else 0,
                "accepted_line_count": 96_304 if index == 0 else 0,
                "word_token_count": 1_313_842 if index == 0 else 0,
                "word_box_correction_count": 22 if index == 0 else 0,
                "word_box_corrected_edge_count": 22 if index == 0 else 0,
                "quarantined_span_count": 0,
                "ordering_quarantined_raw_line_run_count": 0,
                "ordering_quarantined_raw_word_count": 0,
                "noncontiguous_line_identity_count": 0,
                "unresolved": not complete,
            }
        )
    for native_index in range(93):
        ordinal = 1_357 + native_index
        records.append(
            {
                "request_ordinal": ordinal,
                "request_sha256": f"{ordinal:064x}",
                "document_id": document_ids[native_index % 27],
                "route": full._NATIVE_ROUTE,
                "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
                "upstream_origin": None,
                "request": {"render_specification": None},
                "line_axis_count": 0,
                "nonempty_line_axis_count": 0,
                "exact_empty_line_axis_count": 0,
                "accepted_line_count": 0,
                "word_token_count": 0,
                "word_box_correction_count": 0,
                "word_box_corrected_edge_count": 0,
                "quarantined_span_count": 0,
                "ordering_quarantined_raw_line_run_count": 0,
                "ordering_quarantined_raw_word_count": 0,
                "noncontiguous_line_identity_count": 0,
                "unresolved": False,
            }
        )
    grouped = {
        document_id: [item for item in records if item["document_id"] == document_id]
        for document_id in document_ids
    }
    control = {
        "claim_boundary": "AUTHENTICATED_PAGE_READ_ACCOUNTING_ONLY",
        "sealed_plan": {"sha256": full.SEALED_PLAN_SHA256},
        "control_identity_sha256": "c" * 64,
        "failed_v2_authority": {},
        "executor_git": {},
        "executor_implementation_ledger": {},
        "native_reader_contract": {},
    }
    sealed = {"documents": [{"document_id": item} for item in document_ids]}
    monkeypatch.setattr(
        full,
        "_v3_replay_published_control_held",
        lambda *_args, **_kwargs: (
            sealed,
            {},
            {"archive_root": tmp_path / "archive", "manifest_index": {}},
        ),
    )
    monkeypatch.setattr(full, "_v3_validate_output_lock_topology", lambda *_args: None)
    monkeypatch.setattr(full, "_v3_validate_checkpoint_and_index_topology", lambda *_args: None)
    monkeypatch.setattr(
        full,
        "_v3_load_document_checkpoints",
        lambda _root, _control, document_id, *_args, **_kwargs: (
            grouped[document_id],
            "h" * 64,
        ),
    )
    monkeypatch.setattr(
        full,
        "_v3_document_index_payload",
        lambda _control, document_id, document_records, head: {
            "document_id": document_id,
            "request_count": len(document_records),
            "head": head,
        },
    )

    def read_document_index(_root: Path, reference: dict) -> dict:
        document_id = f"sha256:{Path(reference['path']).stem}"
        return {
            "document_id": document_id,
            "request_count": len(grouped[document_id]),
            "head": "h" * 64,
        }

    monkeypatch.setattr(full, "_v3_read_document_index", read_document_index)
    monkeypatch.setattr(
        full,
        "_v3_control_index",
        lambda _control: {item["request_sha256"]: {} for item in records},
    )
    monkeypatch.setattr(
        full,
        "_v3_output_inventory",
        lambda *_args, **_kwargs: {
            "referenced_object_count": 4_254,
            "unique_object_count": 4_254,
        },
    )
    monkeypatch.setattr(full, "_v3_bound_output_file_present", lambda _path: False)

    aggregate = full._v3_build_aggregate_held(tmp_path, tmp_path, control, deep_source_replay=False)
    accounting = aggregate["accounting"]
    assert accounting["request_count"] == 1_449
    assert (accounting["ocr_page_count"], accounting["native_page_count"]) == (
        1_356,
        93,
    )
    assert aggregate["ocr_adoption_accounting"] == {
        "line_axis_count": 96_369,
        "nonempty_line_axis_count": 96_304,
        "exact_empty_line_axis_count": 65,
        "accepted_line_count": 96_304,
        "word_token_count": 1_313_842,
        "complete_page_count": 1_299,
        "terminal_geometry_page_count": 57,
        "corrected_page_count": 20,
        "corrected_word_box_count": 22,
        "corrected_edge_count": 22,
        "copied_object_count": 4_068,
        "source_status_and_origin_preserved": True,
    }
    assert accounting["route_dpi_counts"] == {
        full._OCR_ROUTE: {"200": 1_250, "300": 106},
        full._NATIVE_ROUTE: {"NOT_APPLICABLE": 93},
    }
    assert accounting["ocr_upstream_origin_counts"] == {
        "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY": 24,
        "PINNED_PPOCRV6_FULL_READER": 1_332,
    }
    assert accounting["referenced_object_count"] == 4_254 == 4_068 + 2 * 93
    assert aggregate["status"] == ("COMPLETE_WAVE_1_PAGE_REQUEST_ACCOUNTING_WITH_UNRESOLVED_READS")
    assert all(
        value is False if type(value) is bool else value == 0
        for value in aggregate["safety"].values()
    )
    assert all(accounting[key] == 0 for key in full._ZERO_INTERPRETATION)

    records[0]["word_token_count"] += 1
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="accounting drifted"):
        full._v3_build_aggregate_held(tmp_path, tmp_path, control, deep_source_replay=False)
    records[0]["word_token_count"] -= 1
    records[-1]["status"] = "FOREIGN_NATIVE_STATUS"
    with pytest.raises(full.WaveOneRoleBFullReaderError, match="accounting drifted"):
        full._v3_build_aggregate_held(tmp_path, tmp_path, control, deep_source_replay=False)


@pytest.mark.parametrize("aggregate_present", [False, True])
def test_completed_resume_performs_zero_new_native_or_deep_replay_calls(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    aggregate_present: bool,
) -> None:
    document_ids = _document_ids()
    sealed = {"documents": [{"document_id": item} for item in document_ids]}
    policy = {"execution": {"minimum_free_space_bytes": 0}}
    control = {"control_identity_sha256": "c" * 64}
    aggregate = {"aggregate_identity_sha256": "a" * 64}
    manifest = [["d", ".", 0o755, 2, 0, 1, 1, 1, 1, []]]
    if aggregate_present:
        manifest.append(
            [
                "f",
                "full-reader-aggregate.json",
                0o444,
                1,
                1,
                "b" * 64,
                1,
                1,
                1,
                2,
            ]
        )
    completed = {f"{index:064x}" for index in range(1, 1_450)}
    calls: Counter[str] = Counter()

    def forbidden(name: str):
        def invoke(*_args: object, **_kwargs: object) -> None:
            calls[name] += 1
            raise AssertionError(f"completed resume called {name}")

        return invoke

    monkeypatch.setattr(
        full,
        "_v3_authenticate_plan",
        lambda *_args, **_kwargs: (sealed, policy, {}),
    )
    monkeypatch.setattr(full, "_v3_failed_archive_locks", lambda *_args, **_kwargs: nullcontext(()))
    monkeypatch.setattr(full, "_v3_execution_lease", lambda *_args, **_kwargs: nullcontext(-1))
    monkeypatch.setattr(full, "_v3_document_locks", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(
        full,
        "_v3_preflight_output_temporaries",
        lambda *_args, **_kwargs: (None, deepcopy(manifest)),
    )
    monkeypatch.setattr(full, "_v3_publication_pair_path", lambda *_args: None)
    monkeypatch.setattr(full, "_v3_publication_target_path", lambda *_args: None)
    monkeypatch.setattr(full, "_v3_recover_publication_directory", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(full, "_v3_output_live_manifest", lambda _root: deepcopy(manifest))
    monkeypatch.setattr(full, "_v3_bind_output_reads", lambda *_args, **_kwargs: nullcontext())
    monkeypatch.setattr(full, "_v3_load_published_control", lambda _root: control)
    monkeypatch.setattr(
        full,
        "_v3_replay_published_control_held",
        lambda *_args, **_kwargs: (
            sealed,
            {},
            {"archive_root": tmp_path / "archive", "manifest_index": {}},
        ),
    )
    monkeypatch.setattr(full, "_v3_ensure_capacity", lambda *_args: None)
    monkeypatch.setattr(full, "_v3_output_lock_state", lambda *_args: "FULL_LOCK_SET")
    monkeypatch.setattr(full, "_v3_validate_output_lock_topology", lambda *_args: None)
    monkeypatch.setattr(
        full,
        "_v3_read_partial_run_state",
        lambda *_args, **_kwargs: (
            {item: [] for item in document_ids},
            {item: "h" * 64 for item in document_ids},
            completed,
            {},
            set(),
            {},
            {},
        ),
    )
    monkeypatch.setattr(full, "_v3_recover_object_publications", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        full,
        "_v3_publish_document_indexes",
        lambda *_args, **_kwargs: [{} for _ in range(27)],
    )
    monkeypatch.setattr(full, "_v3_build_aggregate_held", lambda *_args, **_kwargs: aggregate)
    for name in (
        "_v3_source_payload",
        "_v3_replay_partial_native_state",
        "_v3_build_native_payloads",
        "_v3_build_native_record",
        "build_causal_native_text_evidence_v2",
        "render_composited_displayed_page",
    ):
        monkeypatch.setattr(full, name, forbidden(name))

    before = _tree_tokens(tmp_path / full.OUTPUT_RELATIVE_ROOT)
    result = full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
    after = _tree_tokens(tmp_path / full.OUTPUT_RELATIVE_ROOT)
    assert calls == Counter()
    assert before == after == []
    assert result["status"] == (
        "COMPLETE_V3_PAGE_REQUEST_EXECUTION_RESUME_WITH_ZERO_NEW_NATIVE_EVIDENCE_BUILDS"
    )
    assert result["native_read_during_command"] == 0
    assert result["native_orphan_adopted_during_command"] == 0
    assert result["authenticated_published_aggregate_present"] is aggregate_present


def test_completed_resume_real_tree_is_structurally_idempotent_and_zero_new_native(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    document_ids = [f"sha256:{index + 10_000:064x}" for index in range(27)]
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    lock_documents = locks / "documents"
    lock_documents.mkdir(parents=True)
    lease = locks / "full-reader-execution.lease"
    lease.touch(mode=0o600)
    lease.chmod(0o600)
    for document_id in document_ids:
        lock = lock_documents / f"{document_id.removeprefix('sha256:')}.lock"
        lock.touch(mode=0o600)
        lock.chmod(0o600)

    object_root = root / "objects" / "sha256"
    object_root.mkdir(parents=True)
    created_buckets: set[str] = set()

    def put_object(label: str, suffix: str) -> dict[str, object]:
        payload = (f"synthetic-v3-object:{label}\n").encode()
        digest = sha256(payload).hexdigest()
        bucket_name = digest[:2]
        bucket = object_root / bucket_name
        if bucket_name not in created_buckets:
            bucket.mkdir()
            created_buckets.add(bucket_name)
        path = bucket / f"{digest}{suffix}"
        path.write_bytes(payload)
        path.chmod(0o444)
        return {
            "path": path.relative_to(root).as_posix(),
            "sha256": digest,
            "size_bytes": len(payload),
        }

    records: list[dict[str, object]] = []
    for index in range(1_356):
        complete = index < 1_299
        records.append(
            {
                "request_ordinal": index + 1,
                "request_sha256": f"{index + 1:064x}",
                "document_id": document_ids[index % 27],
                "route": full._OCR_ROUTE,
                "status": (
                    "OCR_WORD_BOX_READ_COMPLETE" if complete else "UNRESOLVED_OCR_WORD_BOX_GEOMETRY"
                ),
                "origin": "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY",
                "upstream_origin": (
                    "AUTHENTICATED_SUCCESSFUL_SENTINEL_BYTE_COPY"
                    if index < 24
                    else "PINNED_PPOCRV6_FULL_READER"
                ),
                "request": {"render_specification": {"dpi": 200 if index < 1_250 else 300}},
                "render_ref": put_object(f"ocr-render-{index}", ".png"),
                "backend_payload_ref": put_object(f"ocr-backend-{index}", ".json"),
                "result_ref": put_object(f"ocr-result-{index}", ".json"),
                "line_axis_count": 96_369 if index == 0 else 0,
                "nonempty_line_axis_count": 96_304 if index == 0 else 0,
                "exact_empty_line_axis_count": 65 if index == 0 else 0,
                "accepted_line_count": 96_304 if index == 0 else 0,
                "word_token_count": 1_313_842 if index == 0 else 0,
                "word_box_correction_count": 22 if index == 0 else 0,
                "word_box_corrected_edge_count": 22 if index == 0 else 0,
                "quarantined_span_count": 0,
                "ordering_quarantined_raw_line_run_count": 0,
                "ordering_quarantined_raw_word_count": 0,
                "noncontiguous_line_identity_count": 0,
                "unresolved": not complete,
            }
        )
    for native_index in range(93):
        ordinal = 1_357 + native_index
        records.append(
            {
                "request_ordinal": ordinal,
                "request_sha256": f"{ordinal:064x}",
                "document_id": document_ids[native_index % 27],
                "route": full._NATIVE_ROUTE,
                "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
                "upstream_origin": None,
                "request": {"render_specification": None},
                "render_ref": None,
                "backend_payload_ref": put_object(f"native-backend-{native_index}", ".json"),
                "result_ref": put_object(f"native-result-{native_index}", ".json"),
                "line_axis_count": 0,
                "nonempty_line_axis_count": 0,
                "exact_empty_line_axis_count": 0,
                "accepted_line_count": 0,
                "word_token_count": 0,
                "word_box_correction_count": 0,
                "word_box_corrected_edge_count": 0,
                "quarantined_span_count": 0,
                "ordering_quarantined_raw_line_run_count": 0,
                "ordering_quarantined_raw_word_count": 0,
                "noncontiguous_line_identity_count": 0,
                "unresolved": False,
            }
        )
    grouped = {
        document_id: [item for item in records if item["document_id"] == document_id]
        for document_id in document_ids
    }
    control = {
        "claim_boundary": "AUTHENTICATED_PAGE_READ_ACCOUNTING_ONLY",
        "sealed_plan": {"sha256": full.SEALED_PLAN_SHA256},
        "control_identity_sha256": "c" * 64,
        "failed_v2_authority": {},
        "executor_git": {},
        "executor_implementation_ledger": {},
        "native_reader_contract": {},
        "documents": [
            {
                "document_id": document_id,
                "pages": [
                    {
                        "request_ordinal": item["request_ordinal"],
                        "request_sha256": item["request_sha256"],
                        "route": item["route"],
                    }
                    for item in grouped[document_id]
                ],
            }
            for document_id in document_ids
        ],
    }
    control_path = root / "full-reader-execution-control.json"
    control_path.write_bytes(_canonical(control))
    control_path.chmod(0o444)
    checkpoint_root = root / "checkpoints"
    checkpoint_root.mkdir()
    heads: dict[str, str] = {}
    for document_id in document_ids:
        directory = checkpoint_root / document_id.removeprefix("sha256:")
        directory.mkdir()
        previous = None
        for generation, record in enumerate(grouped[document_id], start=1):
            checkpoint = full._v3_checkpoint_payload(
                control,
                document_id,
                record,
                generation,
                previous,
            )
            payload = _canonical(checkpoint)
            previous = sha256(payload).hexdigest()
            path = directory / f"{generation:04d}-{previous}.json"
            path.write_bytes(payload)
            path.chmod(0o444)
        assert previous is not None
        heads[document_id] = previous

    sealed = {"documents": [{"document_id": item} for item in document_ids]}
    policy = {"execution": {"minimum_free_space_bytes": 0}}
    expected_index = full._v3_control_index(control)
    allowed_object_paths = {
        reference["path"]
        for record in records
        for key in ("render_ref", "backend_payload_ref", "result_ref")
        if (reference := record[key]) is not None
    }
    monkeypatch.setattr(
        full,
        "_v3_authenticate_plan",
        lambda *_args, **_kwargs: (sealed, policy, {}),
    )
    monkeypatch.setattr(full, "_v3_failed_archive_locks", lambda *_args, **_kwargs: nullcontext(()))
    monkeypatch.setattr(full, "_v3_ensure_capacity", lambda *_args: None)

    def load_control(project_root: Path) -> dict:
        payload, identity = full._v3_read_nofollow(
            project_root / full.OUTPUT_RELATIVE_ROOT / control_path.name,
            "synthetic completed control",
        )
        assert stat.S_IMODE(identity.st_mode) == 0o444
        assert identity.st_nlink == 1
        assert payload == _canonical(control)
        return json.loads(payload)

    monkeypatch.setattr(full, "_v3_load_published_control", load_control)
    monkeypatch.setattr(
        full,
        "_v3_replay_published_control_held",
        lambda *_args, **_kwargs: (
            sealed,
            {},
            {"archive_root": tmp_path / "archive", "manifest_index": {}},
        ),
    )
    monkeypatch.setattr(
        full,
        "_v3_load_document_checkpoints",
        lambda _root, _control, document_id, *_args, **_kwargs: (
            grouped[document_id],
            heads[document_id],
        ),
    )
    monkeypatch.setattr(
        full,
        "_v3_read_partial_run_state",
        lambda *_args, **_kwargs: (
            grouped,
            heads,
            set(expected_index),
            expected_index,
            allowed_object_paths,
            {},
            {},
        ),
    )
    forbidden_calls: Counter[str] = Counter()

    def forbidden(name: str):
        def invoke(*_args: object, **_kwargs: object) -> None:
            forbidden_calls[name] += 1
            raise AssertionError(f"completed physical resume called {name}")

        return invoke

    for name in (
        "_v3_source_payload",
        "_v3_replay_partial_native_state",
        "_v3_replay_native_record",
        "_v3_replay_all_native",
        "_v3_replay_all_ocr_renders",
        "_v3_build_native_payloads",
        "_v3_build_native_record",
        "build_causal_native_text_evidence_v2",
        "render_composited_displayed_page",
    ):
        monkeypatch.setattr(full, name, forbidden(name))

    full._v3_publish_document_indexes(tmp_path, control, grouped, heads)
    original_recovery = full._v3_recover_object_publications
    original_index_publisher = full._v3_publish_document_indexes
    structural_calls: Counter[str] = Counter()

    def recover_objects(*args: object, **kwargs: object) -> None:
        structural_calls["object_recovery"] += 1
        original_recovery(*args, **kwargs)

    def publish_indexes(*args: object, **kwargs: object) -> list[dict]:
        structural_calls["index_publish"] += 1
        return original_index_publisher(*args, **kwargs)

    monkeypatch.setattr(full, "_v3_recover_object_publications", recover_objects)
    monkeypatch.setattr(full, "_v3_publish_document_indexes", publish_indexes)

    index_directory = root / "documents"
    index_names = sorted(path.name for path in index_directory.iterdir())
    standalone_name = index_names[0]
    standalone_final = index_directory / standalone_name
    standalone_payload = standalone_final.read_bytes()
    standalone_final.unlink()
    _ignored_final, standalone_temporary = _publish_temp(
        index_directory,
        standalone_name,
        b"synthetic interrupted partial document index",
        mode=0o600,
        linked=False,
    )
    before_standalone = _tree_tokens(root)
    recovered_standalone = full._run_authenticated_full_reader_mutating(
        tmp_path, model_cache=tmp_path
    )
    after_standalone = _tree_tokens(root)
    excluded_standalone = {
        f"documents/{standalone_name}",
        f"documents/{standalone_temporary.name}",
    }
    assert [item for item in before_standalone if item[1] not in excluded_standalone] == [
        item for item in after_standalone if item[1] not in excluded_standalone
    ]
    assert not standalone_temporary.exists()
    assert standalone_final.read_bytes() == standalone_payload
    assert stat.S_IMODE(standalone_final.stat().st_mode) == 0o444
    assert standalone_final.stat().st_nlink == 1
    assert recovered_standalone["native_read_during_command"] == 0

    pair_name = index_names[1]
    pair_final = index_directory / pair_name
    pair_inode = pair_final.stat().st_ino
    pair_temporary = index_directory / f".{pair_name}.{'b' * 32}.tmp"
    os.link(pair_final, pair_temporary)
    before_pair = _tree_tokens(root)
    recovered_pair = full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
    after_pair = _tree_tokens(root)
    excluded_pair = {
        f"documents/{pair_name}",
        f"documents/{pair_temporary.name}",
    }
    assert [item for item in before_pair if item[1] not in excluded_pair] == [
        item for item in after_pair if item[1] not in excluded_pair
    ]
    assert not pair_temporary.exists()
    assert pair_final.stat().st_ino == pair_inode
    assert pair_final.stat().st_nlink == 1
    assert recovered_pair["native_read_during_command"] == 0

    before_unfinalized = full._v3_output_live_manifest(tmp_path)
    unfinalized = full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
    after_unfinalized = full._v3_output_live_manifest(tmp_path)
    assert before_unfinalized == after_unfinalized
    assert unfinalized["authenticated_published_aggregate_present"] is False
    assert unfinalized["native_read_during_command"] == 0
    assert unfinalized["native_orphan_adopted_during_command"] == 0

    deep_replay_calls: Counter[str] = Counter()

    def replay_ocr(*_args: object, **_kwargs: object) -> None:
        deep_replay_calls["ocr"] += 1

    def replay_native(*_args: object, **_kwargs: object) -> None:
        deep_replay_calls["native"] += 1

    monkeypatch.setattr(full, "_v3_replay_all_ocr_renders", replay_ocr)
    monkeypatch.setattr(full, "_v3_replay_all_native", replay_native)
    before_absent_verify = full._v3_output_live_manifest(tmp_path)
    absent_verification = full.verify_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    assert full._v3_output_live_manifest(tmp_path) == before_absent_verify
    assert absent_verification["authenticated_published_aggregate_present"] is False

    with full._v3_bind_output_reads(tmp_path, before_absent_verify):
        aggregate = full._v3_build_aggregate_held(
            tmp_path,
            tmp_path,
            control,
            deep_source_replay=False,
        )
    _aggregate_final, aggregate_temporary = _publish_temp(
        root,
        "full-reader-aggregate.json",
        _canonical(aggregate),
        mode=0o600,
        linked=False,
    )
    before_temporary_verify = full._v3_output_live_manifest(tmp_path)
    with pytest.raises(full.WaveOneRoleBFullReaderError):
        full.verify_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    assert full._v3_output_live_manifest(tmp_path) == before_temporary_verify

    before_first_finalize = _tree_tokens(root)
    first_finalized = full.finalize_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    after_first_finalize = _tree_tokens(root)
    aggregate_relative_names = {
        "full-reader-aggregate.json",
        aggregate_temporary.name,
    }
    assert [item for item in before_first_finalize if item[1] not in aggregate_relative_names] == [
        item for item in after_first_finalize if item[1] not in aggregate_relative_names
    ]
    aggregate_final = root / "full-reader-aggregate.json"
    assert not aggregate_temporary.exists()
    assert aggregate_final.read_bytes() == _canonical(aggregate)
    assert stat.S_IMODE(aggregate_final.stat().st_mode) == 0o444
    assert aggregate_final.stat().st_nlink == 1
    assert first_finalized == aggregate

    before_present_verify = full._v3_output_live_manifest(tmp_path)
    present_verification = full.verify_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    assert full._v3_output_live_manifest(tmp_path) == before_present_verify
    assert present_verification["authenticated_published_aggregate_present"] is True
    assert present_verification["aggregate"] == aggregate

    before_second_finalize = full._v3_output_live_manifest(tmp_path)
    second_finalized = full.finalize_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    after_second_finalize = full._v3_output_live_manifest(tmp_path)
    assert before_second_finalize == after_second_finalize
    assert second_finalized == aggregate

    aggregate_inode = aggregate_final.stat().st_ino
    aggregate_pair = root / f".full-reader-aggregate.json.{'d' * 32}.tmp"
    os.link(aggregate_final, aggregate_pair)
    before_aggregate_pair = _tree_tokens(root)
    pair_finalized = full.finalize_authenticated_full_reader(tmp_path, model_cache=tmp_path)
    after_aggregate_pair = _tree_tokens(root)
    aggregate_pair_names = {"full-reader-aggregate.json", aggregate_pair.name}
    assert [item for item in before_aggregate_pair if item[1] not in aggregate_pair_names] == [
        item for item in after_aggregate_pair if item[1] not in aggregate_pair_names
    ]
    assert not aggregate_pair.exists()
    assert aggregate_final.stat().st_ino == aggregate_inode
    assert aggregate_final.stat().st_nlink == 1
    assert pair_finalized == aggregate

    before_finalized = full._v3_output_live_manifest(tmp_path)
    deep_before_run = deepcopy(deep_replay_calls)
    finalized = full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
    after_finalized = full._v3_output_live_manifest(tmp_path)
    assert before_finalized == after_finalized
    assert deep_replay_calls == deep_before_run
    assert finalized["authenticated_published_aggregate_present"] is True
    assert finalized["native_read_during_command"] == 0
    assert finalized["native_orphan_adopted_during_command"] == 0
    assert structural_calls == Counter({"object_recovery": 4, "index_publish": 4})
    assert deep_replay_calls == Counter({"ocr": 8, "native": 8})
    assert forbidden_calls == Counter()


@pytest.mark.parametrize(
    "crash_stage",
    [
        "backend_tmp_600",
        "backend_tmp_444",
        "backend_pair",
        "lone_backend",
        "result_tmp",
        "result_pair",
        "result_orphan",
        "foreign_object",
    ],
)
def test_next_native_cas_crash_matrix_recovers_once_or_rejects_unchanged(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    crash_stage: str,
) -> None:
    document = full.fitz.open()
    document.new_page(width=400, height=300)
    source_bytes = document.tobytes(garbage=4, deflate=True)
    document.close()
    source_sha = sha256(source_bytes).hexdigest()
    source_document_id = f"sha256:{source_sha}"
    document_ids = sorted(
        [source_document_id] + [f"sha256:{index + 20_000:064x}" for index in range(26)]
    )
    source_path = tmp_path / "synthetic-source.pdf"
    source_path.write_bytes(source_bytes)
    provider_records = []
    for relative in (
        Path("config/ocr/causal-native-text-v1.yaml"),
        Path("config/ocr/native-text-quality-v2.yaml"),
    ):
        payload = (PROJECT_ROOT / relative).read_bytes()
        local_policy = tmp_path / relative
        local_policy.parent.mkdir(parents=True, exist_ok=True)
        local_policy.write_bytes(payload)
        local_policy.chmod(0o444)
        provider_records.append(
            {
                "path": relative.as_posix(),
                "sha256": sha256(payload).hexdigest(),
                "size_bytes": len(payload),
            }
        )
    provider_ledger = {
        "config_records": provider_records,
        "ocr_fallback_allowed": False,
        "provider": "PYMUPDF_CAUSAL_NATIVE_TEXT_VISIBILITY_V1",
        "pymupdf_binding_version": full.fitz.VersionBind,
        "pymupdf_distribution_version": distribution_version("PyMuPDF"),
        "pymupdf_runtime_versions": list(full.fitz.version),
    }
    provider_ledger["sha256"] = sha256(_canonical(provider_ledger)).hexdigest()
    ordering_relative = Path("config/ocr/causal-native-text-evidence-v2.yaml")
    ordering_payload = (PROJECT_ROOT / ordering_relative).read_bytes()
    local_ordering_policy = tmp_path / ordering_relative
    local_ordering_policy.write_bytes(ordering_payload)
    local_ordering_policy.chmod(0o444)
    ordering_identity = {
        "path": ordering_relative.as_posix(),
        "sha256": sha256(ordering_payload).hexdigest(),
        "size_bytes": len(ordering_payload),
    }
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
        "provider_identity_sha256": provider_ledger["sha256"],
        "render_runtime_identity_sha256": None,
        "render_specification": None,
        "role_a_used": False,
        "route": "CAUSAL_NATIVE_TEXT",
        "route_plan_sha256": "e" * 64,
        "schema_used": False,
        "selection_receipt_sha256": "f" * 64,
        "sentinel_sha256": "0" * 64,
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
    }
    request_sha = sha256(_canonical(request)).hexdigest()
    expected_last = {
        "request_ordinal": 1_449,
        "document_id": source_document_id,
        "source_sha256": source_sha,
        "source_size_bytes": len(source_bytes),
        "physical_page": 1,
        "route": full._NATIVE_ROUTE,
        "request_sha256": request_sha,
        "request": request,
    }
    control_identity = "1" * 64
    backend, result = full.build_causal_native_text_evidence_v2(
        request=request,
        request_sha256=request_sha,
        source_bytes=source_bytes,
        document_id=source_document_id,
        physical_page=1,
        provider_runtime_ledger=provider_ledger,
        causal_policy_path=PROJECT_ROOT / "config/ocr/causal-native-text-v1.yaml",
        quality_policy_path=PROJECT_ROOT / "config/ocr/native-text-quality-v2.yaml",
        full_control_identity_sha256=control_identity,
        native_ordering_policy_identity=ordering_identity,
    )
    backend_payload = _canonical(backend)
    result_payload = _canonical(result)
    backend_sha = sha256(backend_payload).hexdigest()
    result_sha = sha256(result_payload).hexdigest()
    assert result["backend_payload_sha256"] == backend_sha

    previous_records: list[dict[str, object]] = []
    ocr_authority_index: dict[str, dict[str, object]] = {}
    for index in range(1_356):
        request_hash = f"{index + 1:064x}"
        document_id = document_ids[index % 27]
        fake_refs = {}
        for ref_index, key in enumerate(("render_ref", "backend_payload_ref", "result_ref")):
            digest = sha256(f"ocr-authority-{index}-{ref_index}".encode()).hexdigest()
            fake_refs[key] = {
                "path": f"objects/sha256/{digest[:2]}/{digest}.json",
                "sha256": digest,
                "size_bytes": 1,
            }
        record = {
            "request_ordinal": index + 1,
            "request_sha256": request_hash,
            "document_id": document_id,
            "route": full._OCR_ROUTE,
            "status": "OCR_WORD_BOX_READ_COMPLETE",
            "origin": "AUTHENTICATED_FAILED_V2_OCR_EVIDENCE_BYTE_COPY",
            "upstream_origin": "PINNED_PPOCRV6_FULL_READER",
            "request": {"render_specification": {"dpi": 200}},
            **fake_refs,
            "line_axis_count": 0,
            "nonempty_line_axis_count": 0,
            "exact_empty_line_axis_count": 0,
            "accepted_line_count": 0,
            "word_token_count": 0,
            "word_box_correction_count": 0,
            "word_box_corrected_edge_count": 0,
            "quarantined_span_count": 0,
            "ordering_quarantined_raw_line_run_count": 0,
            "ordering_quarantined_raw_word_count": 0,
            "noncontiguous_line_identity_count": 0,
            "unresolved": False,
        }
        previous_records.append(record)
        ocr_authority_index[request_hash] = {
            "request": {
                "request_ordinal": index + 1,
                "request_sha256": request_hash,
            },
            "source_refs": fake_refs,
        }
    for native_index in range(92):
        ordinal = 1_357 + native_index
        previous_records.append(
            {
                "request_ordinal": ordinal,
                "request_sha256": f"{ordinal:064x}",
                "document_id": document_ids[native_index % 27],
                "route": full._NATIVE_ROUTE,
                "status": "CAUSAL_NATIVE_TEXT_READ_COMPLETE",
                "origin": "FRESH_SEALED_CAUSAL_NATIVE_TEXT_GATE_V2",
                "upstream_origin": None,
                "request": {"render_specification": None},
                "render_ref": None,
                "backend_payload_ref": None,
                "result_ref": None,
                "line_axis_count": 0,
                "nonempty_line_axis_count": 0,
                "exact_empty_line_axis_count": 0,
                "accepted_line_count": 0,
                "word_token_count": 0,
                "word_box_correction_count": 0,
                "word_box_corrected_edge_count": 0,
                "quarantined_span_count": 0,
                "ordering_quarantined_raw_line_run_count": 0,
                "ordering_quarantined_raw_word_count": 0,
                "noncontiguous_line_identity_count": 0,
                "unresolved": False,
            }
        )
    grouped = {
        document_id: [item for item in previous_records if item["document_id"] == document_id]
        for document_id in document_ids
    }
    control = {
        "claim_boundary": "AUTHENTICATED_PAGE_READ_ACCOUNTING_ONLY",
        "sealed_plan": {"sha256": full.SEALED_PLAN_SHA256},
        "control_identity_sha256": control_identity,
        "failed_v2_authority": {},
        "executor_git": {},
        "executor_implementation_ledger": {},
        "native_reader_contract": {
            "provider_runtime_ledger": provider_ledger,
            "native_ordering_policy_identity": ordering_identity,
            "causal_policy_path": "config/ocr/causal-native-text-v1.yaml",
            "quality_policy_path": "config/ocr/native-text-quality-v2.yaml",
        },
        "documents": [],
    }
    control_pages = [
        {
            "request_ordinal": item["request_ordinal"],
            "request_sha256": item["request_sha256"],
            "route": item["route"],
            "document_id": item["document_id"],
            "source_sha256": item["document_id"].removeprefix("sha256:"),
            "source_size_bytes": 1,
            "physical_page": 1,
            "request": item["request"],
        }
        for item in previous_records
    ] + [expected_last]
    for document_id in document_ids:
        control["documents"].append(
            {
                "document_id": document_id,
                "pages": [item for item in control_pages if item["document_id"] == document_id],
            }
        )
    expected_index = full._v3_control_index(control)
    completed = {item["request_sha256"] for item in previous_records}
    root = _make_output_root(tmp_path)
    locks = root / "locks"
    lock_documents = locks / "documents"
    lock_documents.mkdir(parents=True)
    lease = locks / "full-reader-execution.lease"
    lease.touch(mode=0o600)
    lease.chmod(0o600)
    for document_id in document_ids:
        lock = lock_documents / f"{document_id.removeprefix('sha256:')}.lock"
        lock.touch(mode=0o600)
        lock.chmod(0o600)
    control_path = root / "full-reader-execution-control.json"
    control_path.write_bytes(_canonical(control))
    control_path.chmod(0o444)
    checkpoint_root = root / "checkpoints"
    checkpoint_root.mkdir()
    heads: dict[str, str | None] = {}
    for document_id in document_ids:
        directory = checkpoint_root / document_id.removeprefix("sha256:")
        directory.mkdir()
        previous = None
        for generation, record in enumerate(grouped[document_id], start=1):
            payload = _canonical(
                full._v3_checkpoint_payload(control, document_id, record, generation, previous)
            )
            previous = sha256(payload).hexdigest()
            checkpoint = directory / f"{generation:04d}-{previous}.json"
            checkpoint.write_bytes(payload)
            checkpoint.chmod(0o444)
        heads[document_id] = previous

    def object_path(digest: str) -> Path:
        return root / "objects" / "sha256" / digest[:2] / f"{digest}.json"

    def write_final(digest: str, payload: bytes) -> Path:
        path = object_path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(payload)
        path.chmod(0o444)
        return path

    def write_temporary(
        digest: str, payload: bytes, *, mode: int, linked: bool
    ) -> tuple[Path, Path]:
        path = object_path(digest)
        path.parent.mkdir(parents=True, exist_ok=True)
        return _publish_temp(path.parent, path.name, payload, mode=mode, linked=linked)

    preserved_inodes: dict[str, int] = {}
    if crash_stage == "backend_tmp_600":
        _backend_final, _backend_temporary = write_temporary(
            backend_sha, backend_payload, mode=0o600, linked=False
        )
    elif crash_stage == "backend_tmp_444":
        _backend_final, _backend_temporary = write_temporary(
            backend_sha, backend_payload, mode=0o444, linked=False
        )
    elif crash_stage == "backend_pair":
        backend_final, _backend_temporary = write_temporary(
            backend_sha, backend_payload, mode=0o444, linked=True
        )
        preserved_inodes["backend"] = backend_final.stat().st_ino
    elif crash_stage == "lone_backend":
        backend_final = write_final(backend_sha, backend_payload)
        preserved_inodes["backend"] = backend_final.stat().st_ino
    elif crash_stage == "result_tmp":
        backend_final = write_final(backend_sha, backend_payload)
        preserved_inodes["backend"] = backend_final.stat().st_ino
        _result_final, _result_temporary = write_temporary(
            result_sha, result_payload, mode=0o600, linked=False
        )
    elif crash_stage == "result_pair":
        backend_final = write_final(backend_sha, backend_payload)
        result_final, _result_temporary = write_temporary(
            result_sha, result_payload, mode=0o444, linked=True
        )
        preserved_inodes.update(
            backend=backend_final.stat().st_ino,
            result=result_final.stat().st_ino,
        )
    elif crash_stage == "result_orphan":
        backend_final = write_final(backend_sha, backend_payload)
        result_final = write_final(result_sha, result_payload)
        preserved_inodes.update(
            backend=backend_final.stat().st_ino,
            result=result_final.stat().st_ino,
        )
    else:
        foreign_payload = b"{}\n"
        write_final(sha256(foreign_payload).hexdigest(), foreign_payload)

    sealed = {
        "documents": [
            {
                "document_id": document_id,
                "relative_path": source_path.name,
                "sha256": source_sha,
                "size_bytes": len(source_bytes),
            }
            for document_id in document_ids
        ],
        "causal_native_runtime_ledger": provider_ledger,
    }
    policy = {"execution": {"minimum_free_space_bytes": 0}}
    counters: Counter[str] = Counter()
    original_replay_native = full._v3_replay_native_record

    monkeypatch.setattr(
        full,
        "_v3_authenticate_plan",
        lambda *_args, **_kwargs: (sealed, policy, {}),
    )
    monkeypatch.setattr(full, "_v3_failed_archive_locks", lambda *_args, **_kwargs: nullcontext(()))
    monkeypatch.setattr(full, "_v3_ensure_capacity", lambda *_args: None)
    monkeypatch.setattr(full, "_v3_load_published_control", lambda _root: deepcopy(control))
    monkeypatch.setattr(
        full,
        "_v3_replay_published_control_held",
        lambda *_args, **_kwargs: (
            sealed,
            ocr_authority_index,
            {"archive_root": tmp_path / "archive", "manifest_index": {}},
        ),
    )

    def read_partial_state(
        project_root: Path,
        _control: dict,
        _document_ids: list[str],
        _ocr_index: dict,
        _archive_root: Path,
        _manifest_index: dict,
        *,
        publication_pair_path: str | None,
        publication_target_path: str | None,
        publication_temporary_path: str | None,
        output_manifest: list[list[object]],
    ) -> tuple:
        allowed: set[str] = set()
        with full._v3_bind_output_reads(project_root, output_manifest):
            orphans = full._v3_scan_native_orphans(
                project_root,
                control,
                {},
                publication_pair_path=publication_pair_path,
            )
            allowed.update(
                reference["path"]
                for record in orphans.values()
                for reference in (record["backend_payload_ref"], record["result_ref"])
            )
            if (
                publication_pair_path is None
                and publication_target_path is not None
                and publication_target_path.startswith("objects/sha256/")
            ):
                allowed.add(publication_target_path)
            lone_backends = full._v3_validate_partial_cas_authority(
                project_root,
                control,
                allowed,
                completed,
                publication_pair_path=publication_pair_path,
                publication_temporary_path=publication_temporary_path,
            )
        return (
            grouped,
            heads,
            completed,
            expected_index,
            allowed,
            orphans,
            lone_backends,
        )

    monkeypatch.setattr(full, "_v3_read_partial_run_state", read_partial_state)

    def source_payload(*_args: object, **_kwargs: object) -> tuple[Path, bytes]:
        counters["source_payload"] += 1
        return source_path, source_bytes

    def build_payloads(*_args: object, **_kwargs: object) -> tuple[dict, dict]:
        counters["build_payloads"] += 1
        return deepcopy(backend), deepcopy(result)

    def replay_native(*args: object, **kwargs: object) -> None:
        record = args[3]
        counters["replay_native"] += 1
        if record["request_sha256"] == request_sha:
            original_replay_native(*args, **kwargs)

    monkeypatch.setattr(full, "_v3_source_payload", source_payload)
    monkeypatch.setattr(full, "_v3_build_native_payloads", build_payloads)
    monkeypatch.setattr(full, "_v3_replay_native_record", replay_native)
    monkeypatch.setattr(
        full,
        "_v3_build_aggregate_held",
        lambda *_args, **_kwargs: {"aggregate_identity_sha256": "a" * 64},
    )

    before = full._v3_output_live_manifest(tmp_path)
    if crash_stage == "foreign_object":
        with pytest.raises(full.WaveOneRoleBFullReaderError, match="foreign native backend"):
            full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
        assert full._v3_output_live_manifest(tmp_path) == before
        assert counters == Counter()
        return

    outcome = full._run_authenticated_full_reader_mutating(tmp_path, model_cache=tmp_path)
    backend_final = object_path(backend_sha)
    result_final = object_path(result_sha)
    assert backend_final.read_bytes() == backend_payload
    assert result_final.read_bytes() == result_payload
    assert stat.S_IMODE(backend_final.stat().st_mode) == 0o444
    assert stat.S_IMODE(result_final.stat().st_mode) == 0o444
    assert backend_final.stat().st_nlink == result_final.stat().st_nlink == 1
    assert not list((root / "objects").rglob("*.tmp"))
    observed_object_files = {
        path.relative_to(root).as_posix() for path in (root / "objects").rglob("*.json")
    }
    assert observed_object_files == {
        backend_final.relative_to(root).as_posix(),
        result_final.relative_to(root).as_posix(),
    }
    if "backend" in preserved_inodes:
        assert backend_final.stat().st_ino == preserved_inodes["backend"]
    if "result" in preserved_inodes:
        assert result_final.stat().st_ino == preserved_inodes["result"]
    target_records = grouped[source_document_id]
    assert target_records[-1]["request_sha256"] == request_sha
    checkpoint_names = os.listdir(checkpoint_root / source_sha)
    assert len(checkpoint_names) == len(target_records)
    assert not any(name.endswith(".tmp") for name in checkpoint_names)
    assert len(list((root / "documents").glob("*.json"))) == 27
    orphan_case = crash_stage in {"result_pair", "result_orphan"}
    assert outcome["native_read_during_command"] == (0 if orphan_case else 1)
    assert outcome["native_orphan_adopted_during_command"] == (1 if orphan_case else 0)
    assert counters["build_payloads"] == (0 if orphan_case else 1)
    assert counters["source_payload"] > 0
    assert counters["replay_native"] >= 92
