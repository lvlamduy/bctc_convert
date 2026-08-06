from __future__ import annotations

import base64
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from bctc_ai.core.atomic import atomic_write_json
from bctc_ai.core.hashing import sha256_file
from bctc_ai.storage.s3_snapshot import (
    AwsCli,
    S3SnapshotError,
    collect_inventory,
    hydrate_from_snapshot,
    load_settings,
    offload_local_assets,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = PROJECT_ROOT / "config/backup/s3-v1.toml"


def _sha(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


class FakeS3Runner:
    def __init__(
        self,
        objects: dict[str, bytes] | None = None,
        *,
        versioning_status: str | None = "Enabled",
    ) -> None:
        self.objects = dict(objects or {})
        self.versioning_status = versioning_status
        self.commands: list[list[str]] = []

    @staticmethod
    def _value(command: list[str], option: str) -> str:
        return command[command.index(option) + 1]

    def _head_payload(self, key: str) -> dict[str, object]:
        payload = self.objects[key]
        digest = _sha(payload)
        return {
            "ContentLength": len(payload),
            "ChecksumSHA256": base64.b64encode(bytes.fromhex(digest)).decode("ascii"),
            "Metadata": {"sha256": digest, "format": "raw-v1"},
            "ServerSideEncryption": "AES256",
        }

    def __call__(
        self, command: list[str] | tuple[str, ...], environment: object
    ) -> subprocess.CompletedProcess[str]:
        del environment
        command = list(command)
        self.commands.append(command)
        if command[1:3] == ["sts", "get-caller-identity"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "Account": "000000000000",
                        "Arn": "arn:aws:iam::000000000000:user/test",
                    }
                ),
                "",
            )
        if command[1:3] == ["s3api", "head-bucket"]:
            return subprocess.CompletedProcess(
                command, 0, json.dumps({"BucketRegion": "us-east-1"}), ""
            )
        if command[1:3] == ["s3api", "get-bucket-versioning"]:
            payload = (
                {"Status": self.versioning_status} if self.versioning_status is not None else {}
            )
            return subprocess.CompletedProcess(command, 0, json.dumps(payload), "")
        if command[1:3] == ["s3api", "get-bucket-encryption"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "ServerSideEncryptionConfiguration": {
                            "Rules": [
                                {"ApplyServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}
                            ]
                        }
                    }
                ),
                "",
            )
        if command[1:3] == ["s3api", "get-public-access-block"]:
            return subprocess.CompletedProcess(
                command,
                0,
                json.dumps(
                    {
                        "PublicAccessBlockConfiguration": {
                            "BlockPublicAcls": True,
                            "IgnorePublicAcls": True,
                            "BlockPublicPolicy": True,
                            "RestrictPublicBuckets": True,
                        }
                    }
                ),
                "",
            )
        if command[1] == "--version":
            return subprocess.CompletedProcess(command, 0, "aws-cli/test", "")
        if command[1:3] == ["s3api", "head-object"]:
            key = self._value(command, "--key")
            if key not in self.objects:
                return subprocess.CompletedProcess(command, 1, "", "404 Not Found")
            return subprocess.CompletedProcess(command, 0, json.dumps(self._head_payload(key)), "")
        if command[1:3] == ["s3api", "put-object"]:
            key = self._value(command, "--key")
            assert self._value(command, "--if-none-match") == "*"
            assert self._value(command, "--checksum-algorithm") == "SHA256"
            assert "delete-object" not in command
            if key in self.objects:
                return subprocess.CompletedProcess(command, 1, "", "412 PreconditionFailed")
            payload = Path(self._value(command, "--body")).read_bytes()
            assert self._value(command, "--checksum-sha256") == base64.b64encode(
                hashlib.sha256(payload).digest()
            ).decode("ascii")
            self.objects[key] = payload
            return subprocess.CompletedProcess(command, 0, "{}", "")
        if command[1:3] == ["s3api", "get-object"]:
            key = self._value(command, "--key")
            owner_index = command.index("--expected-bucket-owner")
            destination = Path(command[owner_index + 2])
            destination.write_bytes(self.objects[key])
            return subprocess.CompletedProcess(command, 0, "{}", "")
        raise AssertionError(f"unexpected fake AWS command: {command}")


def test_s3_config_is_immutable_checksum_first_and_has_no_delete_surface():
    settings = load_settings(CONFIG_PATH)

    assert settings.bucket == "test-s3-duylv"
    assert settings.profile == "bctc-backup"
    assert settings.put_if_none_match == "*"
    assert settings.include_sha256_checksum
    assert not settings.delete_operations_enabled
    assert not settings.overwrite_operations_enabled
    assert settings.production_requires_versioning
    assert settings.production_requires_full_content_restore
    assert not settings.allow_unversioned_immutable_snapshot


def test_s3_preflight_rejects_an_unversioned_bucket():
    client = AwsCli(load_settings(CONFIG_PATH), runner=FakeS3Runner(versioning_status=None))

    with pytest.raises(S3SnapshotError, match="versioning is not enabled"):
        client.preflight()


def test_inventory_requires_every_pdf_to_match_the_registered_hash(tmp_path):
    project = tmp_path / "project"
    pdf = project / "vietstock_bctc" / "AAA" / "2026" / "report.pdf"
    pdf.parent.mkdir(parents=True)
    pdf.write_bytes(b"registered-pdf")
    (project / "vietstock_bctc" / "manifest.csv").write_text(
        "path,status\nreport.pdf,ok\n", encoding="utf-8"
    )
    registry = project / "data" / "registered" / "source_registry.jsonl"
    registry.parent.mkdir(parents=True)
    registry.write_text(
        json.dumps(
            {
                "relative_path": pdf.relative_to(project).as_posix(),
                "kind": "PDF",
                "state": "REGISTERED",
                "hash_verified_stable": True,
                "size_bytes": pdf.stat().st_size,
                "sha256": sha256_file(pdf),
            }
        )
        + "\n",
        encoding="utf-8",
    )
    output = project / "output" / "result.json"
    output.parent.mkdir()
    output.write_text("{}\n", encoding="utf-8")
    dump = project / "financial_20_02_2022.gz"
    dump.write_bytes(b"dump")
    atomic_write_json(
        registry.parent / "mongodb_dump_registry.json",
        {
            "archive": {
                "path": dump.relative_to(project).as_posix(),
                "size_bytes": dump.stat().st_size,
                "sha256": sha256_file(dump),
            }
        },
    )
    database = project / "data" / "local" / "historical_weak_reference.duckdb"
    database.parent.mkdir()
    database.write_bytes(b"duckdb")
    atomic_write_json(
        registry.parent / "historical_weak_reference_registry.json",
        {
            "database": {
                "path": database.relative_to(project).as_posix(),
                "size_bytes": database.stat().st_size,
                "sha256": sha256_file(database),
            }
        },
    )

    assets = collect_inventory(project, load_settings(CONFIG_PATH))
    by_class = {asset.asset_class for asset in assets}
    assert len(assets) == 5
    assert by_class == {
        "source_pdf",
        "source_acquisition_metadata",
        "generated_output",
        "mongodb_dump",
        "historical_weak_reference",
    }

    pdf.write_bytes(b"drifted")
    with pytest.raises(S3SnapshotError, match="registered size drift"):
        collect_inventory(project, load_settings(CONFIG_PATH))


def test_put_content_uses_conditional_sha256_checked_encrypted_write(tmp_path):
    payload = tmp_path / "payload.bin"
    payload.write_bytes(b"immutable")
    digest = sha256_file(payload)
    runner = FakeS3Runner()
    client = AwsCli(load_settings(CONFIG_PATH), runner=runner)
    client.preflight()

    result = client.put_content(
        payload,
        key=f"bctc-ai/objects/sha256/{digest[:2]}/{digest}",
        digest=digest,
    )

    assert result.disposition == "UPLOADED"
    put = next(command for command in runner.commands if "put-object" in command)
    assert put[put.index("--if-none-match") + 1] == "*"
    assert put[put.index("--server-side-encryption") + 1] == "AES256"


def test_offload_is_dry_by_default_then_hydrates_exact_file_without_overwrite(tmp_path):
    project = tmp_path / "project"
    source = project / "vietstock_bctc" / "AAA" / "2026" / "report.pdf"
    source.parent.mkdir(parents=True)
    source_payload = b"source-to-offload"
    source.write_bytes(source_payload)
    sentinel = project / "keep.txt"
    sentinel.write_text("keep", encoding="utf-8")
    digest = sha256_file(source)
    object_key = f"bctc-ai/objects/sha256/{digest[:2]}/{digest}"
    snapshot_id = "20260806T000000000000Z-deadbeef0000"
    manifest = {
        "format_version": 1,
        "snapshot_id": snapshot_id,
        "s3": {"bucket": "test-s3-duylv", "prefix": "bctc-ai"},
        "files": [
            {
                "asset_class": "source_pdf",
                "logical_path": source.relative_to(project).as_posix(),
                "object_key": object_key,
                "sha256": digest,
                "size_bytes": len(source_payload),
            }
        ],
    }
    evidence = tmp_path / "evidence"
    evidence.mkdir()
    manifest_path = evidence / "snapshot-manifest.json"
    atomic_write_json(manifest_path, manifest)
    manifest_sha256 = sha256_file(manifest_path)
    manifest_key = f"bctc-ai/snapshots/{snapshot_id}/manifest-{manifest_sha256}.json"
    run_record_path = evidence / "s3-backup-run.json"
    atomic_write_json(
        run_record_path,
        {
            "snapshot_id": snapshot_id,
            "manifest": {"key": manifest_key, "sha256": manifest_sha256},
            "off_machine_status": "PASS",
            "restore_status": "PASS",
        },
    )
    run_record_sha256 = sha256_file(run_record_path)
    run_record_key = f"bctc-ai/runs/{snapshot_id}/run-{run_record_sha256}.json"
    runner = FakeS3Runner(
        {
            object_key: source_payload,
            manifest_key: manifest_path.read_bytes(),
            run_record_key: run_record_path.read_bytes(),
        }
    )

    plan = offload_local_assets(
        project,
        config_path=CONFIG_PATH,
        manifest_path=manifest_path,
        run_record_path=run_record_path,
        asset_classes=["source_pdf"],
        apply=False,
        runner=runner,
    )
    assert isinstance(plan, dict)
    assert plan["file_count"] == 1
    assert source.exists()

    applied = offload_local_assets(
        project,
        config_path=CONFIG_PATH,
        manifest_path=manifest_path,
        run_record_path=run_record_path,
        asset_classes=["source_pdf"],
        apply=True,
        runner=runner,
    )
    assert applied.removed_file_count == 1
    assert not source.exists()
    assert sentinel.read_text(encoding="utf-8") == "keep"

    hydrated = hydrate_from_snapshot(
        project,
        config_path=CONFIG_PATH,
        manifest_key=manifest_key,
        manifest_sha256=manifest_sha256,
        logical_paths=[source.relative_to(project).as_posix()],
        runner=runner,
    )
    assert hydrated.restored_file_count == 1
    assert source.read_bytes() == source_payload

    source.write_bytes(b"local-conflict")
    with pytest.raises(S3SnapshotError, match="refuses to overwrite"):
        hydrate_from_snapshot(
            project,
            config_path=CONFIG_PATH,
            manifest_key=manifest_key,
            manifest_sha256=manifest_sha256,
            logical_paths=[source.relative_to(project).as_posix()],
            runner=runner,
        )
