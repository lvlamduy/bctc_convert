from __future__ import annotations

import copy
import io
import json
import os
import stat
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage import codex_session_backup as session_backup
from bctc_ai.storage.codex_session_backup import (
    CodexSessionBackupError,
    backup_sessions_to_s3,
    create_session_archive,
    verify_session_archive,
)

_CREATED_AT = datetime(2026, 8, 7, tzinfo=UTC)
_EXPECTED_V2_DETECTORS = [
    "github_classic_token",
    "github_fine_grained_token",
    "openai_project_key",
    "google_api_key",
    "aws_access_key_id",
    "aws_secret_assignment",
    "private_key_header",
]


@dataclass(frozen=True)
class _Upload:
    disposition: str = "UPLOADED"


class _RecordingClient:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.objects: dict[str, bytes] = {}

    def preflight(self) -> None:
        self.calls.append("preflight")

    def put_content(self, path: Path, *, key: str, digest: str) -> _Upload:
        self.calls.append("put_content")
        assert sha256_file(path) == digest
        self.objects[key] = path.read_bytes()
        return _Upload()

    def download_content(self, *, key: str, destination: Path, digest: str) -> None:
        self.calls.append("download_content")
        destination.write_bytes(self.objects[key])
        assert sha256_file(destination) == digest


def _create_clean_archive(tmp_path: Path, *, staging_name: str = "staging"):
    sessions = tmp_path / f"sessions-{staging_name}"
    sessions.mkdir()
    source = sessions / "rollout.jsonl"
    source.write_text('{"event":"clean"}\n', encoding="utf-8")
    result = create_session_archive(
        sessions,
        tmp_path / staging_name,
        host="test-host",
        created_at=_CREATED_AT,
    )
    return sessions, source, result


def _manifest_for_archive(
    result,
    archive_path: Path,
    destination: Path,
    *,
    payload: dict | None = None,
) -> tuple[Path, dict]:
    manifest = payload or json.loads(result.manifest_path.read_text(encoding="utf-8"))
    manifest["archive"]["sha256"] = sha256_file(archive_path)
    manifest["archive"]["size_bytes"] = archive_path.stat().st_size
    destination.write_text(json.dumps(manifest), encoding="utf-8")
    return destination, manifest


def _copy_archive_members(source_path: Path, destination: tarfile.TarFile) -> None:
    with tarfile.open(source_path, "r:gz") as source:
        for member in source.getmembers():
            if member.isfile():
                stream = source.extractfile(member)
                assert stream is not None
                with stream:
                    destination.addfile(member, stream)
            else:
                destination.addfile(member)


def test_session_archive_v2_contains_exact_inventory_and_restores_metadata(tmp_path):
    codex = tmp_path / ".codex"
    sessions = codex / "sessions"
    first = sessions / "2026" / "08" / "07" / "rollout.jsonl"
    first.parent.mkdir(parents=True)
    first.write_text('{"event":"one"}\n', encoding="utf-8")
    second = sessions / "archived" / "rollout.jsonl"
    second.parent.mkdir(parents=True)
    second.write_text('{"event":"two"}\n', encoding="utf-8")
    secret_outside_scope = codex / "auth.json"
    secret_outside_scope.write_text('{"token":"outside-scope"}\n', encoding="utf-8")
    first_mtime_ns = 1_700_000_000_123_456_000
    second_mtime_ns = 1_700_000_001_987_654_000
    first.chmod(0o600)
    second.chmod(0o640)
    first_stat = first.stat()
    second_stat = second.stat()
    os.utime(first, ns=(first_stat.st_atime_ns, first_mtime_ns))
    os.utime(second, ns=(second_stat.st_atime_ns, second_mtime_ns))

    staging = tmp_path / "staging"
    result = create_session_archive(
        sessions,
        staging,
        host="test-host",
        created_at=_CREATED_AT,
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.file_count == 2
    assert manifest["format_version"] == 2
    assert manifest["policy"] == "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V2"
    assert manifest["secret_scan"] == {
        "detectors": _EXPECTED_V2_DETECTORS,
        "policy": "FAIL_CLOSED_KNOWN_CREDENTIAL_FORMATS_V2",
        "scanned_bytes": first.stat().st_size + second.stat().st_size,
        "scanned_file_count": 2,
        "status": "PASS",
    }
    assert {item["path"] for item in manifest["files"]} == {
        "2026/08/07/rollout.jsonl",
        "archived/rollout.jsonl",
    }
    with tarfile.open(result.archive_path, "r:gz") as archive:
        assert archive.getnames() == [
            "sessions",
            "sessions/2026",
            "sessions/archived",
            "sessions/2026/08",
            "sessions/2026/08/07",
            "sessions/2026/08/07/rollout.jsonl",
            "sessions/archived/rollout.jsonl",
        ]
    assert not (staging / "session-snapshot").exists()
    assert not (staging / "local-verified-restore").exists()

    restore = tmp_path / "restore"
    assert verify_session_archive(result.archive_path, result.manifest_path, restore)
    restored_first = restore / "sessions" / "2026/08/07/rollout.jsonl"
    restored_second = restore / "sessions" / "archived/rollout.jsonl"
    assert sha256_file(restored_first) == sha256_file(first)
    assert sha256_file(restored_second) == sha256_file(second)
    assert restored_first.stat().st_mtime_ns == first_mtime_ns
    assert restored_second.stat().st_mtime_ns == second_mtime_ns
    assert restored_first.stat().st_mode & 0o777 == 0o600
    assert restored_second.stat().st_mode & 0o777 == 0o640


_AWS_SECRET = "S" * 40
_DETECTOR_CASES = [
    ("ghp_" + "A" * 36, "ghp_" + "A" * 36, "github_classic_token"),
    ("github_pat_" + "B" * 40, "github_pat_" + "B" * 40, "github_fine_grained_token"),
    ("sk-proj-" + "C" * 48, "sk-proj-" + "C" * 48, "openai_project_key"),
    ("AIza" + "G" * 35, "AIza" + "G" * 35, "google_api_key"),
    ("AKIA" + "D" * 16, "AKIA" + "D" * 16, "aws_access_key_id"),
    (
        f'\\"aws_secret_access_key\\": \\"{_AWS_SECRET}\\"',
        _AWS_SECRET,
        "aws_secret_assignment",
    ),
    (f'{{"SecretAccessKey":"{_AWS_SECRET}"}}', _AWS_SECRET, "aws_secret_assignment"),
    (
        "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----",
        "-----BEGIN " + "ENCRYPTED PRIVATE KEY-----",
        "private_key_header",
    ),
]


@pytest.mark.parametrize(("payload", "raw_secret", "detector"), _DETECTOR_CASES)
def test_session_archive_v2_rejects_known_credentials_without_echo_or_residue(
    tmp_path,
    payload,
    raw_secret,
    detector,
):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    source = sessions / "rollout.jsonl"
    source.write_text(payload + "\n", encoding="utf-8")
    staging = tmp_path / "staging"

    with pytest.raises(CodexSessionBackupError) as captured:
        create_session_archive(
            sessions,
            staging,
            host="test-host",
            created_at=_CREATED_AT,
        )

    message = str(captured.value)
    assert "session secret scan rejected data" in message
    assert detector in message
    assert raw_secret not in message
    assert source.read_text(encoding="utf-8") == payload + "\n"
    assert not (staging / "session-snapshot").exists()
    assert not (staging / "codex-sessions.tar.gz").exists()
    assert not (staging / "codex-sessions.manifest.json").exists()
    assert not (staging / "local-verified-restore").exists()


def test_secret_bearing_symlink_path_is_rejected_without_echo(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    outside = tmp_path / "outside"
    outside.write_text("clean", encoding="utf-8")
    token = "sk-proj-" + "P" * 48
    (sessions / token).symlink_to(outside)
    staging = tmp_path / "staging"

    with pytest.raises(CodexSessionBackupError) as captured:
        create_session_archive(
            sessions,
            staging,
            host="test-host",
            created_at=_CREATED_AT,
        )

    assert token not in str(captured.value)
    assert str(outside) not in str(captured.value)
    assert not (staging / "session-snapshot").exists()


def test_missing_secret_bearing_source_path_is_not_echoed(tmp_path):
    token = "sk-proj-" + "Q" * 48
    missing_source = tmp_path / token

    with pytest.raises(CodexSessionBackupError) as captured:
        create_session_archive(
            missing_source,
            tmp_path / "staging",
            host="test-host",
            created_at=_CREATED_AT,
        )

    assert token not in str(captured.value)
    assert str(missing_source) not in str(captured.value)


def test_session_secret_scan_rejects_before_any_client_call(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    token = "github_pat_" + "R" * 40
    source = sessions / "rollout.jsonl"
    source.write_text(f'{{"token":"{token}"}}\n', encoding="utf-8")
    client = _RecordingClient()

    with pytest.raises(CodexSessionBackupError) as captured:
        backup_sessions_to_s3(
            source_root=sessions,
            client=client,  # type: ignore[arg-type]
            prefix="codex-sessions",
            host="test-host",
            created_at=_CREATED_AT,
        )

    assert client.calls == []
    assert token not in str(captured.value)
    assert source.exists()


def test_local_archive_verification_precedes_client_preflight(tmp_path, monkeypatch):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "rollout.jsonl").write_text('{"event":"clean"}\n', encoding="utf-8")
    events: list[str] = []
    original_verify = session_backup.verify_session_archive

    def recording_verify(*args, **kwargs):
        events.append("verify")
        return original_verify(*args, **kwargs)

    class OrderedClient(_RecordingClient):
        def preflight(self) -> None:
            events.append("preflight")
            super().preflight()

    monkeypatch.setattr(session_backup, "verify_session_archive", recording_verify)
    client = OrderedClient()

    result = backup_sessions_to_s3(
        source_root=sessions,
        client=client,  # type: ignore[arg-type]
        prefix="codex-sessions",
        host="test-host",
        created_at=_CREATED_AT,
    )

    assert result.restore_verified is True
    assert events == ["verify", "preflight", "verify"]
    assert client.calls == [
        "preflight",
        "put_content",
        "put_content",
        "download_content",
        "download_content",
    ]


def test_post_scan_archive_injection_fails_local_verify_before_any_client_call(
    tmp_path, monkeypatch
):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    (sessions / "rollout.jsonl").write_text('{"event":"clean"}\n', encoding="utf-8")
    token = "sk-proj-" + "T" * 48
    secret_payload = f'{{"token":"{token}"}}\n'.encode()
    original_write_archive = session_backup._write_archive

    def write_then_inject(snapshot_root, archive_path, records):
        original_write_archive(snapshot_root, archive_path, records)
        forged = archive_path.with_name("post-scan-forged.tar.gz")
        with tarfile.open(forged, "w:gz", format=tarfile.PAX_FORMAT) as archive:
            _copy_archive_members(archive_path, archive)
            member = tarfile.TarInfo("sessions/injected.jsonl")
            member.size = len(secret_payload)
            member.mode = 0o600
            archive.addfile(member, io.BytesIO(secret_payload))
        os.replace(forged, archive_path)

    monkeypatch.setattr(session_backup, "_write_archive", write_then_inject)
    client = _RecordingClient()

    with pytest.raises(CodexSessionBackupError) as captured:
        backup_sessions_to_s3(
            source_root=sessions,
            client=client,  # type: ignore[arg-type]
            prefix="codex-sessions",
            host="test-host",
            created_at=_CREATED_AT,
        )

    assert client.calls == []
    assert token not in str(captured.value)


def test_restore_rejects_duplicate_member_body_and_cleans_destination(tmp_path):
    sessions, source, result = _create_clean_archive(tmp_path)
    token = "ghp_" + "U" * 36
    secret_payload = f'{{"token":"{token}"}}\n'.encode()
    forged_archive = tmp_path / "duplicate.tar.gz"
    with tarfile.open(forged_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add(sessions, arcname="sessions", recursive=False)
        secret_member = tarfile.TarInfo("sessions/rollout.jsonl")
        secret_member.size = len(secret_payload)
        secret_member.mode = source.stat().st_mode & 0o777
        archive.addfile(secret_member, io.BytesIO(secret_payload))
        archive.add(source, arcname="sessions/rollout.jsonl", recursive=False)
    forged_manifest, _payload = _manifest_for_archive(
        result,
        forged_archive,
        tmp_path / "duplicate.manifest.json",
    )
    restore = tmp_path / "duplicate-restore"

    with pytest.raises(CodexSessionBackupError) as captured:
        verify_session_archive(forged_archive, forged_manifest, restore)

    assert token not in str(captured.value)
    assert not restore.exists()


def test_restore_rejects_unexpected_secret_named_directory_without_echo(tmp_path):
    _sessions, _source, result = _create_clean_archive(tmp_path)
    token = "sk-proj-" + "V" * 48
    forged_archive = tmp_path / "extra-directory.tar.gz"
    with tarfile.open(forged_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        _copy_archive_members(result.archive_path, archive)
        extra = tarfile.TarInfo(f"sessions/{token}")
        extra.type = tarfile.DIRTYPE
        extra.mode = 0o700
        archive.addfile(extra)
    forged_manifest, _payload = _manifest_for_archive(
        result,
        forged_archive,
        tmp_path / "extra-directory.manifest.json",
    )
    restore = tmp_path / "extra-directory-restore"

    with pytest.raises(CodexSessionBackupError) as captured:
        verify_session_archive(forged_archive, forged_manifest, restore)

    assert token not in str(captured.value)
    assert not restore.exists()


@pytest.mark.parametrize("legacy", [False, True])
def test_v2_and_legacy_v1_restore_rescan_archive_bodies_with_v2_detectors(tmp_path, legacy):
    sessions, source, result = _create_clean_archive(
        tmp_path, staging_name="staging-legacy" if legacy else "staging-v2"
    )
    token = "sk-proj-" + "W" * 48
    secret_file = tmp_path / ("legacy-secret" if legacy else "v2-secret")
    secret_file.write_text(f'{{"token":"{token}"}}\n', encoding="utf-8")
    os.chmod(secret_file, source.stat().st_mode & 0o777)
    forged_archive = tmp_path / ("legacy-secret.tar.gz" if legacy else "v2-secret.tar.gz")
    with tarfile.open(forged_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add(sessions, arcname="sessions", recursive=False)
        archive.add(secret_file, arcname="sessions/rollout.jsonl", recursive=False)

    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    file_record = payload["files"][0]
    file_record["size_bytes"] = secret_file.stat().st_size
    file_record["sha256"] = sha256_file(secret_file)
    file_record["mode"] = stat.S_IMODE(secret_file.stat().st_mode)
    file_record["mtime_ns"] = secret_file.stat().st_mtime_ns
    payload["summary"]["total_bytes"] = secret_file.stat().st_size
    payload["secret_scan"]["scanned_bytes"] = secret_file.stat().st_size
    if legacy:
        payload["format_version"] = 1
        payload["policy"] = "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V1"
        payload.pop("secret_scan")
    forged_manifest, _payload = _manifest_for_archive(
        result,
        forged_archive,
        tmp_path / ("legacy-secret.json" if legacy else "v2-secret.json"),
        payload=payload,
    )
    restore = tmp_path / ("legacy-secret-restore" if legacy else "v2-secret-restore")

    with pytest.raises(CodexSessionBackupError) as captured:
        verify_session_archive(forged_archive, forged_manifest, restore)

    assert "openai_project_key" in str(captured.value)
    assert token not in str(captured.value)
    assert not restore.exists()


def test_clean_legacy_v1_manifest_restores_only_after_current_rescan(tmp_path):
    sessions, source, result = _create_clean_archive(tmp_path)
    legacy_archive = tmp_path / "legacy-v1.tar.gz"
    with tarfile.open(legacy_archive, "w:gz", format=tarfile.PAX_FORMAT) as archive:
        archive.add(sessions, arcname="sessions", recursive=True)
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    payload["format_version"] = 1
    payload["policy"] = "CODEX_SESSION_DATA_ONLY_IMMUTABLE_S3_V1"
    payload.pop("secret_scan")
    legacy_manifest, _payload = _manifest_for_archive(
        result,
        legacy_archive,
        tmp_path / "legacy-v1.manifest.json",
        payload=payload,
    )
    restore = tmp_path / "legacy-v1-restore"

    assert verify_session_archive(legacy_archive, legacy_manifest, restore)
    assert sha256_file(restore / "sessions" / "rollout.jsonl") == sha256_file(source)


def test_v2_restore_rejects_missing_or_drifted_secret_scan_contract(tmp_path):
    _sessions, source, result = _create_clean_archive(tmp_path)
    original = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    drifted_scans = [
        None,
        {**original["secret_scan"], "policy": "UNEXPECTED"},
        {**original["secret_scan"], "status": "FAIL"},
        {**original["secret_scan"], "detectors": ["github_classic_token"]},
        {**original["secret_scan"], "scanned_file_count": 2},
        {**original["secret_scan"], "scanned_bytes": source.stat().st_size + 1},
    ]
    for index, secret_scan in enumerate(drifted_scans):
        payload = copy.deepcopy(original)
        if secret_scan is None:
            payload.pop("secret_scan")
        else:
            payload["secret_scan"] = secret_scan
        manifest = tmp_path / f"drifted-{index}.json"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        restore = tmp_path / f"restore-{index}"

        with pytest.raises(CodexSessionBackupError):
            verify_session_archive(result.archive_path, manifest, restore)

        assert not restore.exists()


def test_restore_rejects_secret_scan_counts_that_disagree_with_summary(tmp_path):
    _sessions, _source, result = _create_clean_archive(tmp_path)
    payload = json.loads(result.manifest_path.read_text(encoding="utf-8"))
    payload["summary"]["total_bytes"] += 1
    payload["secret_scan"]["scanned_bytes"] += 1
    manifest = tmp_path / "drifted-summary.json"
    manifest.write_text(json.dumps(payload), encoding="utf-8")
    restore = tmp_path / "restore-drifted-summary"

    with pytest.raises(CodexSessionBackupError, match="summary counts drifted"):
        verify_session_archive(result.archive_path, manifest, restore)

    assert not restore.exists()


def test_secret_crossing_scan_block_boundary_is_rejected_and_cleaned(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    token = ("ghp_" + "X" * 36).encode()
    payload = b"." * (session_backup._SECRET_SCAN_BLOCK_BYTES - 2) + token + b"."
    (sessions / "rollout.jsonl").write_bytes(payload)
    staging = tmp_path / "staging"

    with pytest.raises(CodexSessionBackupError) as captured:
        create_session_archive(
            sessions,
            staging,
            host="test-host",
            created_at=_CREATED_AT,
        )

    assert token.decode() not in str(captured.value)
    assert not (staging / "session-snapshot").exists()
    assert not (staging / "codex-sessions.tar.gz").exists()
