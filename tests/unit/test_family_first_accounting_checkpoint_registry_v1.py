from __future__ import annotations

import hashlib
import json
from pathlib import Path

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1

ROOT = Path(__file__).resolve().parents[2]
REGISTRY = ROOT / "data/registered/family_first_accounting_checkpoints_v1.json"


def _read(path: Path) -> bytes:
    payload = path.read_bytes()
    assert path.is_file() and not path.is_symlink()
    return payload


def test_registered_family_checkpoint_binds_live_artifacts_and_trust_closure() -> None:
    registry = json.loads(_read(REGISTRY).decode("utf-8"))
    assert set(registry) == {
        "authority",
        "checkpoints",
        "format_version",
        "registry_id",
        "state",
    }
    material = dict(registry)
    registry_id = material.pop("registry_id")
    assert registry_id == "ffacrv1:registry:" + canonical_json_sha256_v1(material)
    assert registry["authority"] == {
        "artifact_bytes_required": True,
        "bank_file_page_period_scope_used_for_matching_or_mapping": False,
        "canonical_export_or_production_authority": False,
        "document_packet_roots_recomputed": True,
        "persisted_artifact_self_authenticating": False,
        "public_exact_replay_required": True,
    }
    assert len(registry["checkpoints"]) == 1
    checkpoint = registry["checkpoints"][0]
    assert checkpoint["family_id"] == "TRADING_SECURITIES"
    assert checkpoint["upstream_ocr_replay_count"] == 0
    assert checkpoint["metrics"] == {
        "document_count": 140,
        "not_observed_proposal_count": 26,
        "unresolved_document_count": 78,
        "verified_document_count": 36,
        "verified_mapping_count": 126,
    }
    for ref in [
        checkpoint["evidence_ref"],
        checkpoint["mapping_ref"],
        *checkpoint["implementation_refs"],
        *checkpoint["spec_refs"],
    ]:
        payload = _read(ROOT / ref["path"])
        assert len(payload) == ref["size_bytes"]
        assert hashlib.sha256(payload).hexdigest() == ref["sha256"]
    evidence = json.loads(_read(ROOT / checkpoint["evidence_ref"]["path"]).decode("utf-8"))
    mapping = json.loads(_read(ROOT / checkpoint["mapping_ref"]["path"]).decode("utf-8"))
    assert evidence["sweep_id"] == checkpoint["evidence_ref"]["sweep_id"]
    assert mapping["mapping_id"] == checkpoint["mapping_ref"]["mapping_id"]
    assert mapping["evidence_sweep_id"] == evidence["sweep_id"]
    assert mapping["metrics"] == checkpoint["metrics"]
