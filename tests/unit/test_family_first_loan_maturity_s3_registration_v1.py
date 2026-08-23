from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RECEIPT_PATH = ROOT / ("docs/experiments/E-0172-family-first-loan-maturity-s3-registration-v1.json")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt_digest(receipt: dict[str, object]) -> str:
    material = dict(receipt)
    material.pop("receipt_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def test_e0172_registration_is_self_hash_bound_and_closed() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    assert set(receipt) == {
        "authority",
        "checkpoint",
        "claim_boundary",
        "experiment_id",
        "family_id",
        "format_version",
        "generated_output_objects",
        "receipt_id",
        "seal_ref",
        "state",
    }
    assert receipt["receipt_id"] == "e0172:receipt:" + _receipt_digest(receipt)
    assert receipt["state"] == "REGISTERED"
    assert receipt["experiment_id"] == "E-0172"
    assert receipt["family_id"] == "LOAN_MATURITY_BUCKETS"

    tampered = copy.deepcopy(receipt)
    tampered["checkpoint"]["restore"]["status"] = "FAIL"
    assert "e0172:receipt:" + _receipt_digest(tampered) != receipt["receipt_id"]


def test_e0172_registration_binds_seal_and_every_generated_output() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    seal_ref = receipt["seal_ref"]
    seal_path = ROOT / seal_ref["path"]
    seal = json.loads(seal_path.read_text(encoding="utf-8"))
    assert seal_path.stat().st_size == seal_ref["size_bytes"]
    assert _sha(seal_path) == seal_ref["sha256"]
    assert seal["seal_id"] == seal_ref["seal_id"]
    assert seal["sweep_id"] == seal_ref["sweep_id"]
    assert seal["git_commit"] == seal_ref["engine_git_commit"]

    objects = {item["role"]: item for item in receipt["generated_output_objects"]}
    assert set(objects) == {
        "formal_result",
        "hosted_full_page_png",
        "hosted_slot_1_raw_response",
        "hosted_slot_2_raw_response",
    }
    expected_refs = {"formal_result": seal["formal_result_ref"]}
    expected_refs.update(seal["restored_snapshot_refs"])
    for role, reference in expected_refs.items():
        remote = objects[role]
        assert {key: remote[key] for key in ("logical_path", "sha256", "size_bytes")} == {
            "logical_path": reference["path"],
            "sha256": reference["sha256"],
            "size_bytes": reference["size_bytes"],
        }
        assert remote["object_key"] == (
            f"bctc-ai/objects/sha256/{remote['sha256'][:2]}/{remote['sha256']}"
        )
        assert remote["version_id"]
        assert remote["head_metadata_hash_size_version_verified"] is True


def test_e0172_checkpoint_crosslinks_manifest_run_restore_and_scan() -> None:
    receipt = json.loads(RECEIPT_PATH.read_text(encoding="utf-8"))
    checkpoint = receipt["checkpoint"]
    checkpoint_id = "20260823T131218475925Z-195457c13a5d"
    assert checkpoint["checkpoint_id"] == checkpoint_id
    assert checkpoint["source_git_commit"] == ("195457c13a5d22ea789f2a4a8f4458dc7046fbd2")
    assert checkpoint["manifest"] == {
        "download_sha256_verified": True,
        "head_metadata_hash_size_version_verified": True,
        "key": (
            f"bctc-ai/project-checkpoints/{checkpoint_id}/"
            "manifest-23a663dd9158449e6dc59988724dc6760a58e7c7deff68672ac85408d99be2c1.json"
        ),
        "sha256": ("23a663dd9158449e6dc59988724dc6760a58e7c7deff68672ac85408d99be2c1"),
        "size_bytes": 8290,
        "version_id": "2_ZF6IPKz0nFLznrX22QkF26LHks0hsi",
    }
    assert checkpoint["run_record"] == {
        "download_sha256_verified": True,
        "head_metadata_hash_size_version_verified": True,
        "key": (
            f"bctc-ai/project-checkpoint-runs/{checkpoint_id}/"
            "run-0ac92bff057803a8e4eee313041525bf685c5aee6d4fbcaafc069e7e7e266da0.json"
        ),
        "sha256": ("0ac92bff057803a8e4eee313041525bf685c5aee6d4fbcaafc069e7e7e266da0"),
        "size_bytes": 2583,
        "status": "PASS",
        "version_id": "rlpNHj897mZ6zup1hsvEyGccuWjQwRHx",
    }
    assert checkpoint["inventory"] == {
        "generated_output_file_count": 4,
        "logical_bytes": 28406342,
        "logical_file_count": 7,
        "unique_object_count": 7,
    }
    assert checkpoint["restore"] == {
        "catalog_head_verified_count": 7,
        "control_plane_restore_verified": True,
        "generated_output_restore_count": 4,
        "git_bundle_verified": True,
        "logical_file_restore_count": 7,
        "manifest_download_verified": True,
        "parent_full_content_stream_verified": True,
        "status": "PASS",
        "unique_object_download_count": 7,
    }
    assert checkpoint["selected_output_credential_scan"] == {
        "scanned_bytes": 5238157,
        "scanned_file_count": 4,
        "status": "PASS",
    }
    assert receipt["authority"] == {
        "credentials_persisted": False,
        "exact_incremental_restore_verified": True,
        "generated_outputs_restore_verified": True,
        "mapping_or_schema_authority_added": False,
        "numeric_or_ocr_authority_added": False,
        "production_or_export_authority_added": False,
        "public_exact_replay_assets_registered": True,
        "s3_durability_registration": True,
    }
