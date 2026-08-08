from __future__ import annotations

import base64
import json
import subprocess
from datetime import UTC, datetime
from pathlib import Path

import pytest
from openpyxl import Workbook
from PIL import Image

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.s3_incremental_checkpoint import (
    POLICY_ID,
    S3IncrementalCheckpointError,
    create_incremental_project_checkpoint,
)
from bctc_ai.storage.s3_snapshot import UploadResult, load_settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SETTINGS = load_settings(PROJECT_ROOT / "config/backup/s3-v1.toml")


class FakeCheckpointClient:
    def __init__(self, settings, objects: dict[str, bytes]) -> None:
        self.settings = settings
        self.objects = dict(objects)
        self.operations: list[str] = []
        self.preflight_count = 0

    def preflight(self):
        self.preflight_count += 1
        self.operations.append("preflight")
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
        self.operations.append(f"put:{key}")
        return UploadResult(key, digest, len(payload), disposition, "version-test")

    def download_content(self, *, key, destination, digest):
        destination = Path(destination)
        assert not destination.exists()
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(self.objects[key])
        assert sha256_file(destination) == digest
        self.operations.append(f"get:{key}")

    def head_object(self, key):
        payload = self.objects.get(key)
        if payload is None:
            return None
        digest = sha256_file_bytes(payload)
        self.operations.append(f"head:{key}")
        return {
            "ContentLength": len(payload),
            "Metadata": {"sha256": digest},
            "ChecksumSHA256": base64.b64encode(bytes.fromhex(digest)).decode("ascii"),
            "ServerSideEncryption": self.settings.server_side_encryption,
            "VersionId": "version-test",
        }

    def verify_head(self, *, key, digest, size_bytes, payload):
        assert payload is not None
        assert payload["ContentLength"] == size_bytes
        assert payload["Metadata"]["sha256"] == digest
        assert payload["ChecksumSHA256"] == base64.b64encode(bytes.fromhex(digest)).decode("ascii")
        assert payload["ServerSideEncryption"] == self.settings.server_side_encryption


def sha256_file_bytes(payload: bytes) -> str:
    import hashlib

    return hashlib.sha256(payload).hexdigest()


def _git(project: Path, *arguments: str) -> None:
    subprocess.run(["git", *arguments], cwd=project, check=True, capture_output=True)


def _project(tmp_path: Path) -> Path:
    project = tmp_path / "project"
    output = project / "output" / "development"
    output.mkdir(parents=True)
    (output / "result.json").write_text('{"status":"PASS"}\n', encoding="utf-8")
    (output / "evidence.bin").write_bytes(b"bounded-evidence")
    workbook = Workbook()
    workbook.active["A1"] = "checkpoint"
    workbook.save(output / "result.xlsx")
    Image.new("RGB", (2, 2), "white").save(output / "evidence.png")
    (project / "README.md").write_text("checkpoint fixture\n", encoding="utf-8")
    (project / ".gitignore").write_text("output/\n", encoding="utf-8")
    _git(project, "init")
    _git(project, "config", "user.name", "test")
    _git(project, "config", "user.email", "test@example.com")
    _git(project, "add", "README.md", ".gitignore")
    _git(project, "commit", "-m", "test")
    _git(project, "remote", "add", "origin", "https://example.invalid/repo.git")
    return project


def _parent(tmp_path: Path) -> tuple[str, str, str, str, dict[str, bytes]]:
    manifest = {
        "format_version": 1,
        "snapshot_id": "passing-full-parent",
        "s3": {"bucket": SETTINGS.bucket, "prefix": SETTINGS.prefix},
    }
    manifest_path = tmp_path / "parent-manifest.json"
    manifest_sha = atomic_write_json(manifest_path, manifest)
    manifest_key = "bctc-ai/snapshots/passing-full-parent/manifest.json"
    run = {
        "format_version": 1,
        "snapshot_id": "passing-full-parent",
        "manifest": {"key": manifest_key, "sha256": manifest_sha},
        "restore": {"full_content_stream_verified": True},
        "production_status": "PASS",
        "restore_status": "PASS",
    }
    run_path = tmp_path / "parent-run.json"
    run_sha = atomic_write_json(run_path, run)
    run_key = "bctc-ai/runs/passing-full-parent/run.json"
    return (
        manifest_key,
        manifest_sha,
        run_key,
        run_sha,
        {manifest_key: manifest_path.read_bytes(), run_key: run_path.read_bytes()},
    )


def _run(project: Path, tmp_path: Path, client: FakeCheckpointClient):
    manifest_key, manifest_sha, run_key, run_sha, _objects = _parent(tmp_path)
    return create_incremental_project_checkpoint(
        project,
        settings=SETTINGS,
        selected_paths=["output/development"],
        parent_manifest_key=manifest_key,
        parent_manifest_sha256=manifest_sha,
        parent_run_record_key=run_key,
        parent_run_record_sha256=run_sha,
        client=client,
        created_at=datetime(2026, 8, 8, 12, 0, tzinfo=UTC),
        workers=2,
    )


def test_incremental_checkpoint_binds_parent_and_fully_restores_every_asset(tmp_path):
    project = _project(tmp_path)
    manifest_key, _manifest_sha, run_key, _run_sha, objects = _parent(tmp_path)
    client = FakeCheckpointClient(SETTINGS, objects)

    result = _run(project, tmp_path, client)

    assert result.restore_verified
    assert result.run_record_verified
    assert result.logical_file_count == 7
    assert result.generated_output_file_count == 4
    assert result.uploaded_object_count == 7
    manifest = json.loads(client.objects[result.manifest_key])
    assert manifest["policy_id"] == POLICY_ID
    assert manifest["parent_full_snapshot"]["snapshot_id"] == "passing-full-parent"
    assert manifest["scope"]["excluded"] == [
        "source_pdf_corpus",
        "codex_sessions",
        "authentication_and_credentials",
        "virtual_environments",
        "model_weights_and_caches",
        "mongodb_runtime_data",
    ]
    assert manifest["scope"]["selected_output_credential_scan"]["status"] == "PASS"
    assert {record["asset_class"] for record in manifest["files"]} == {
        "control_plane",
        "generated_output",
        "git_bundle",
    }
    assert not any(
        record["logical_path"].startswith(("vietstock_bctc/", ".codex/", ".venv/"))
        for record in manifest["files"]
    )
    run = json.loads(client.objects[result.run_record_key])
    assert run["status"] == "PASS"
    assert run["restore"]["logical_file_restore_count"] == 7
    assert run["restore"]["generated_output_restore_count"] == 4
    assert run["restore"]["control_plane_restore_verified"] is True
    assert run["restore"]["git_bundle_verified"] is True
    assert {
        validation.rsplit("::", 1)[1] for validation in run["restore"]["sample_validations"]
    } == {
        "JSON_PARSE_PASS",
        "PNG_DECODE_VERIFY_PASS",
        "XLSX_ZIP_STRUCTURE_PASS",
    }
    assert client.operations.index(f"get:{manifest_key}") < min(
        index
        for index, operation in enumerate(client.operations)
        if operation.startswith("put:bctc-ai/objects/sha256/")
    )
    manifest_put = client.operations.index(f"put:{result.manifest_key}")
    assert all(
        index < manifest_put
        for index, operation in enumerate(client.operations)
        if operation.startswith("put:bctc-ai/objects/sha256/")
    )
    assert manifest_put < client.operations.index(f"put:{result.run_record_key}")
    assert f"head:{result.run_record_key}" in client.operations
    assert f"get:{result.run_record_key}" in client.operations
    assert f"get:{run_key}" in client.operations


def test_incremental_checkpoint_rejects_secret_output_before_aws_preflight(tmp_path):
    project = _project(tmp_path)
    secret = project / "output" / "development" / "secret.txt"
    secret.write_text("ghp_" + "A" * 32, encoding="utf-8")
    _manifest_key, _manifest_sha, _run_key, _run_sha, objects = _parent(tmp_path)
    client = FakeCheckpointClient(SETTINGS, objects)

    with pytest.raises(S3IncrementalCheckpointError, match="credential scan rejected"):
        _run(project, tmp_path, client)

    assert client.preflight_count == 0
    assert not any(operation.startswith("put:") for operation in client.operations)


def test_incremental_checkpoint_rejects_sensitive_output_path(tmp_path):
    project = _project(tmp_path)
    (project / "output" / ".env").write_text("NOT_A_REAL_SECRET=fixture\n", encoding="utf-8")
    _manifest_key, _manifest_sha, _run_key, _run_sha, objects = _parent(tmp_path)
    client = FakeCheckpointClient(SETTINGS, objects)

    with pytest.raises(S3IncrementalCheckpointError, match="credential-path pattern"):
        create_incremental_project_checkpoint(
            project,
            settings=SETTINGS,
            selected_paths=["output"],
            parent_manifest_key="unused",
            parent_manifest_sha256="0" * 64,
            parent_run_record_key="unused",
            parent_run_record_sha256="0" * 64,
            client=client,
        )

    assert client.preflight_count == 0


def test_incremental_checkpoint_rejects_dirty_git_before_aws(tmp_path):
    project = _project(tmp_path)
    (project / "README.md").write_text("dirty\n", encoding="utf-8")
    _manifest_key, _manifest_sha, _run_key, _run_sha, objects = _parent(tmp_path)
    client = FakeCheckpointClient(SETTINGS, objects)

    with pytest.raises(Exception, match="clean Git worktree"):
        _run(project, tmp_path, client)

    assert client.preflight_count == 0


def test_incremental_checkpoint_rejects_selection_outside_output(tmp_path):
    project = _project(tmp_path)
    _manifest_key, _manifest_sha, _run_key, _run_sha, objects = _parent(tmp_path)
    client = FakeCheckpointClient(SETTINGS, objects)

    with pytest.raises(S3IncrementalCheckpointError, match="output/ paths only"):
        create_incremental_project_checkpoint(
            project,
            settings=SETTINGS,
            selected_paths=["README.md"],
            parent_manifest_key="unused",
            parent_manifest_sha256="0" * 64,
            parent_run_record_key="unused",
            parent_run_record_sha256="0" * 64,
            client=client,
        )

    assert client.preflight_count == 0
