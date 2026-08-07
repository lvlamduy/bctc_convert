from __future__ import annotations

import json
import os
import tarfile
from datetime import UTC, datetime

import pytest

from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.codex_session_backup import (
    CodexSessionBackupError,
    create_session_archive,
    verify_session_archive,
)


def test_session_archive_contains_only_session_tree_and_restores_hashes_and_times(tmp_path):
    codex = tmp_path / ".codex"
    sessions = codex / "sessions"
    first = sessions / "2026" / "08" / "07" / "rollout.jsonl"
    first.parent.mkdir(parents=True)
    first.write_text('{"event":"one"}\n', encoding="utf-8")
    second = sessions / "archived" / "rollout.jsonl"
    second.parent.mkdir(parents=True)
    second.write_text('{"event":"two"}\n', encoding="utf-8")
    secret = codex / "auth.json"
    secret.write_text('{"token":"forbidden"}\n', encoding="utf-8")
    first_mtime_ns = 1_700_000_000_123_456_789
    second_mtime_ns = 1_700_000_001_987_654_321
    first.touch()
    second.touch()
    first.chmod(0o600)
    second.chmod(0o640)
    first_stat = first.stat()
    second_stat = second.stat()
    first_mtime_ns -= first_mtime_ns % 1_000
    second_mtime_ns -= second_mtime_ns % 1_000
    first.touch()
    second.touch()
    os.utime(first, ns=(first_stat.st_atime_ns, first_mtime_ns))
    os.utime(second, ns=(second_stat.st_atime_ns, second_mtime_ns))

    result = create_session_archive(
        sessions,
        tmp_path / "staging",
        host="test-host",
        created_at=datetime(2026, 8, 7, tzinfo=UTC),
    )
    manifest = json.loads(result.manifest_path.read_text(encoding="utf-8"))

    assert result.file_count == 2
    assert {item["path"] for item in manifest["files"]} == {
        "2026/08/07/rollout.jsonl",
        "archived/rollout.jsonl",
    }
    with tarfile.open(result.archive_path, "r:gz") as archive:
        assert all("auth.json" not in member.name for member in archive.getmembers())
    assert verify_session_archive(
        result.archive_path,
        result.manifest_path,
        tmp_path / "restore",
    )
    restored_first = tmp_path / "restore" / "sessions" / "2026/08/07/rollout.jsonl"
    restored_second = tmp_path / "restore" / "sessions" / "archived/rollout.jsonl"
    assert sha256_file(restored_first) == sha256_file(first)
    assert sha256_file(restored_second) == sha256_file(second)
    assert restored_first.stat().st_mtime_ns == first_mtime_ns
    assert restored_second.stat().st_mtime_ns == second_mtime_ns
    assert restored_first.stat().st_mode & 0o777 == 0o600
    assert restored_second.stat().st_mode & 0o777 == 0o640


def test_session_archive_rejects_symlinks(tmp_path):
    sessions = tmp_path / "sessions"
    sessions.mkdir()
    outside = tmp_path / "auth.json"
    outside.write_text("secret", encoding="utf-8")
    (sessions / "link").symlink_to(outside)

    with pytest.raises(CodexSessionBackupError, match="symlinks are forbidden"):
        create_session_archive(
            sessions,
            tmp_path / "staging",
            host="test-host",
            created_at=datetime(2026, 8, 7, tzinfo=UTC),
        )
