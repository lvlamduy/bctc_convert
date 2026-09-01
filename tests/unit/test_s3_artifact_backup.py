from __future__ import annotations

import json
import subprocess
import threading
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.s3_artifact_backup import (
    S3ArtifactBackupError,
    backup_artifacts_to_s3,
    collect_artifacts,
)
from bctc_ai.storage.s3_snapshot import UploadResult, load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = load_settings(PROJECT_ROOT / "config/backup/s3-v1.toml")


class FakeArtifactClient:
    def __init__(self, settings, objects: dict[str, bytes]) -> None:
        self.settings = settings
        self.objects = dict(objects)
        self._restore_lock = threading.Lock()
        self._restore_active = 0
        self.max_parallel_restores = 0

    def preflight(self):
        return {
            "authenticated_principal": "arn:aws:iam::000000000000:user/test",
            "bucket": self.settings.bucket,
            "bucket_region": self.settings.region,
            "default_encryption": ["AES256"],
            "public_access_block": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            },
            "versioning_status": "Enabled",
            "aws_cli": "aws-cli/test",
        }

    def put_content(self, path, *, key, digest):
        payload = Path(path).read_bytes()
        assert sha256_file(Path(path)) == digest
        disposition = "REUSED_VERIFIED" if key in self.objects else "UPLOADED"
        if key in self.objects:
            assert self.objects[key] == payload
        self.objects[key] = payload
        return UploadResult(key, digest, len(payload), disposition, "version-test")

    def download_content(self, *, key, destination, digest):
        is_artifact = "/objects/sha256/" in key
        if is_artifact:
            with self._restore_lock:
                self._restore_active += 1
                self.max_parallel_restores = max(self.max_parallel_restores, self._restore_active)
        try:
            if is_artifact:
                time.sleep(0.02)
            destination = Path(destination)
            assert not destination.exists()
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(self.objects[key])
            assert sha256_file(destination) == digest
        finally:
            if is_artifact:
                with self._restore_lock:
                    self._restore_active -= 1


def _git(project: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=project, check=True, capture_output=True)


def test_bounded_artifact_backup_links_passing_parent_and_restores_every_file(tmp_path):
    project = tmp_path / "project"
    output = project / "output" / "recovery"
    output.mkdir(parents=True)
    (output / "one.json").write_text('{"one":1}\n', encoding="utf-8")
    (output / "two.bin").write_bytes(b"two")
    (project / "README.md").write_text("test\n", encoding="utf-8")
    (project / ".gitignore").write_text("output/\n", encoding="utf-8")
    _git(project, "init")
    _git(project, "config", "user.name", "test")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "add", "README.md", ".gitignore")
    _git(project, "commit", "-m", "test")
    _git(project, "remote", "add", "origin", "https://example.invalid/repo.git")

    parent_manifest = {
        "format_version": 1,
        "snapshot_id": "parent",
        "s3": {"bucket": SETTINGS.bucket, "prefix": SETTINGS.prefix},
    }
    parent_run = {
        "format_version": 1,
        "snapshot_id": "parent",
        "manifest": {},
        "restore": {"full_content_stream_verified": True},
        "production_status": "PASS",
        "restore_status": "PASS",
    }
    parent_manifest_path = tmp_path / "parent-manifest.json"
    parent_run_path = tmp_path / "parent-run.json"
    parent_manifest_sha = atomic_write_json(parent_manifest_path, parent_manifest)
    parent_manifest_key = "bctc-ai/snapshots/parent/manifest.json"
    parent_run["manifest"] = {
        "key": parent_manifest_key,
        "sha256": parent_manifest_sha,
    }
    parent_run_sha = atomic_write_json(parent_run_path, parent_run)
    parent_run_key = "bctc-ai/runs/parent/run.json"
    client = FakeArtifactClient(
        SETTINGS,
        {
            parent_manifest_key: parent_manifest_path.read_bytes(),
            parent_run_key: parent_run_path.read_bytes(),
        },
    )

    result = backup_artifacts_to_s3(
        project,
        settings=SETTINGS,
        selected_paths=["output/recovery"],
        parent_manifest_key=parent_manifest_key,
        parent_manifest_sha256=parent_manifest_sha,
        parent_run_record_key=parent_run_key,
        parent_run_record_sha256=parent_run_sha,
        label="r-test",
        client=client,
        created_at=datetime(2026, 8, 7, tzinfo=UTC),
    )

    assert result.file_count == 2
    assert result.uploaded_object_count == 2
    assert result.restore_verified
    assert client.max_parallel_restores == 2
    manifest = json.loads(client.objects[result.manifest_key])
    assert manifest["parent_full_snapshot"]["snapshot_id"] == "parent"
    assert {item["logical_path"] for item in manifest["files"]} == {
        "output/recovery/one.json",
        "output/recovery/two.bin",
    }
    run = json.loads(client.objects[result.run_record_key])
    assert run["status"] == "PASS"
    assert run["all_incremental_objects_restore_verified"] is True


def test_artifact_backup_refuses_paths_outside_output(tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    secret = project / ".env"
    secret.write_text("TOKEN=forbidden\n", encoding="utf-8")

    with pytest.raises(S3ArtifactBackupError, match="output/ paths only"):
        collect_artifacts(project, [secret], SETTINGS)
