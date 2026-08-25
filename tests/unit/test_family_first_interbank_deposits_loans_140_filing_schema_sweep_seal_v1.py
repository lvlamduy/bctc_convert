from __future__ import annotations

import copy
import hashlib
import json
import stat
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SEAL_PATH = ROOT / (
    "docs/experiments/"
    "E-0178-family-first-interbank-deposits-loans-140-filing-schema-sweep-seal-v1.json"
)


def _sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _seal_digest(seal: dict[str, object]) -> str:
    material = copy.deepcopy(seal)
    material.pop("seal_id")
    canonical = json.dumps(
        material, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode()
    return hashlib.sha256(canonical).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def test_interbank_family_seal_is_hash_bound_closed_and_tamper_sensitive() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    assert seal["seal_id"] == "e0178:seal:" + _seal_digest(seal)
    assert seal["format_version"] == (
        "FAMILY_FIRST_INTERBANK_DEPOSITS_LOANS_140_FILING_SCHEMA_SWEEP_SEAL_V1"
    )
    assert seal["state"] == "COMPLETE"
    assert seal["family_id"] == "INTERBANK_DEPOSITS_AND_LOANS"
    assert seal["git_commit"] == "827d5a736e4816c1f1fea014f9a746c444212355"
    assert seal["metrics"] == {
        "document_count": 140,
        "ready_for_schema_review_document_count": 126,
        "not_observed_document_count": 14,
        "unresolved_document_count": 0,
        "verified_document_count": 126,
        "verified_mapping_count": 763,
        "unique_topology_document_count": 100,
    }
    assert sum(item["document_count"] for item in seal["bank_summary"]) == 140
    assert sum(item["verified_document_count"] for item in seal["bank_summary"]) == 126
    assert sum(item["not_observed_document_count"] for item in seal["bank_summary"]) == 14
    assert sum(item["verified_mapping_count"] for item in seal["bank_summary"]) == 763
    assert seal["not_observed_document_ordinals"] == [
        66,
        68,
        77,
        78,
        79,
        80,
        81,
        82,
        83,
        84,
        131,
        132,
        133,
        134,
    ]
    for mutate in (
        lambda value: value["metrics"].__setitem__("unresolved_document_count", 1),
        lambda value: value["formal_evidence_ref"].__setitem__("size_bytes", 1),
        lambda value: value["formal_mapping_ref"].__setitem__("sha256", "0" * 64),
        lambda value: value["authority"].__setitem__(
            "accounting_backsolve_or_invented_value_authority", True
        ),
    ):
        tampered = copy.deepcopy(seal)
        mutate(tampered)
        assert "e0178:seal:" + _seal_digest(tampered) != seal["seal_id"]


def test_interbank_family_seal_tracked_refs_and_store_binding_match_disk() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    for group in ("input_refs", "implementation_refs"):
        for name, reference in seal[group].items():
            if name == "region_retrieval_database":
                continue
            path = ROOT / reference["path"]
            assert path.stat().st_size == reference["size_bytes"]
            assert _sha(path) == reference["sha256"]

    manifest_ref = seal["input_refs"]["document_evidence_manifest"]
    manifest = json.loads((ROOT / manifest_ref["path"]).read_text(encoding="utf-8"))
    assert (
        manifest["manifest_id"] == seal["input_identities"]["document_evidence_store_manifest_id"]
    )
    assert manifest["metrics"] == {
        "document_count": 140,
        "line_count": 667224,
        "page_count": 8947,
    }
    assert manifest["database_ref"] == seal["input_refs"]["region_retrieval_database"]
    database_ref = manifest["database_ref"]
    database = ROOT / database_ref["path"]
    if database.exists():
        assert database.stat().st_size == database_ref["size_bytes"]
        assert _sha(database) == database_ref["sha256"]


def test_interbank_family_formal_pair_matches_seal_when_available() -> None:
    seal = json.loads(SEAL_PATH.read_text(encoding="utf-8"))
    evidence_path = ROOT / seal["formal_evidence_ref"]["path"]
    mapping_path = ROOT / seal["formal_mapping_ref"]["path"]
    if not evidence_path.exists() and not mapping_path.exists():
        return
    assert evidence_path.exists() and mapping_path.exists()

    artifacts = []
    for path, reference in (
        (evidence_path, seal["formal_evidence_ref"]),
        (mapping_path, seal["formal_mapping_ref"]),
    ):
        payload = path.read_bytes()
        value = json.loads(payload)
        assert payload == _canonical_bytes(value)
        assert path.stat().st_size == reference["size_bytes"]
        assert _sha(path) == reference["sha256"]
        assert stat.S_IMODE(path.stat().st_mode) == int(reference["mode"], 8)
        assert path.stat().st_nlink == 1
        artifacts.append(value)
    evidence, mapping = artifacts

    assert evidence["sweep_id"] == seal["sweep_id"] == mapping["evidence_sweep_id"]
    assert mapping["mapping_id"] == seal["mapping_id"]
    assert evidence["family_id"] == mapping["family_id"] == seal["family_id"]
    assert evidence["metrics"] == {
        "document_count": 140,
        "evidence_ready_for_schema_review_count": 126,
        "mapping_verified_count": 0,
        "not_observed_count": 14,
        "unique_topology_document_count": 100,
        "unresolved_document_count": 0,
    }
    assert mapping["metrics"] == {
        "document_count": 140,
        "not_observed_proposal_count": 14,
        "unresolved_document_count": 0,
        "verified_document_count": 126,
        "verified_mapping_count": 763,
    }
    assert mapping["schema_graph_ref"] == seal["input_refs"]["schema_graph"]
    assert evidence["input_indices"] == {
        "numeric_receipt_id": seal["input_identities"]["numeric_receipt_id"],
        "semantic_index_id": seal["input_identities"]["semantic_index_id"],
    }

    evidence_by_ordinal = {trial["document_ordinal"]: trial for trial in evidence["trials"]}
    mapping_by_ordinal = {trial["document_ordinal"]: trial for trial in mapping["trials"]}
    assert list(evidence_by_ordinal) == list(range(1, 141))
    assert list(mapping_by_ordinal) == list(range(1, 141))
    assert Counter(trial["evidence_status"] for trial in evidence["trials"]) == {
        "READY_FOR_SCHEMA_MAPPING_REVIEW_PROPOSAL_ONLY": 126,
        "NOT_OBSERVED_PROPOSAL_ONLY": 14,
    }
    assert Counter(trial["mapping_status"] for trial in mapping["trials"]) == {
        "VERIFIED_BY_CODEX": 126,
        "NOT_OBSERVED_PROPOSAL_ONLY": 14,
    }
    assert all(trial["unresolved_reasons"] == [] for trial in evidence["trials"])
    assert all(trial["unresolved_reasons"] == [] for trial in mapping["trials"])

    not_observed = []
    bank_metrics: dict[str, Counter[str]] = {}
    for ordinal in range(1, 141):
        evidence_trial = evidence_by_ordinal[ordinal]
        mapping_trial = mapping_by_ordinal[ordinal]
        assert evidence_trial["source_pdf_ref"] == mapping_trial["source_pdf_ref"]
        assert evidence_trial["private_provenance"] == mapping_trial["private_provenance"]
        bank = evidence_trial["private_provenance"]["bank"]
        bank_metrics.setdefault(bank, Counter())["document_count"] += 1
        if evidence_trial["evidence_status"] == "NOT_OBSERVED_PROPOSAL_ONLY":
            not_observed.append(ordinal)
            bank_metrics[bank]["not_observed_document_count"] += 1
            assert mapping_trial["mapping_status"] == "NOT_OBSERVED_PROPOSAL_ONLY"
            assert mapping_trial["mappings"] == []
        else:
            bank_metrics[bank]["verified_document_count"] += 1
            bank_metrics[bank]["verified_mapping_count"] += len(mapping_trial["mappings"])
            assert mapping_trial["mapping_status"] == "VERIFIED_BY_CODEX"
            assert mapping_trial["mappings"]
    assert not_observed == seal["not_observed_document_ordinals"]
    assert [
        {
            "bank": item["bank"],
            "document_count": bank_metrics[item["bank"]]["document_count"],
            "verified_document_count": bank_metrics[item["bank"]]["verified_document_count"],
            "not_observed_document_count": bank_metrics[item["bank"]][
                "not_observed_document_count"
            ],
            "verified_mapping_count": bank_metrics[item["bank"]]["verified_mapping_count"],
        }
        for item in seal["bank_summary"]
    ] == seal["bank_summary"]
    assert (
        evidence["authority"]["bank_file_page_period_scope_used_for_matching_or_routing"] is False
    )
    assert mapping["authority"]["bank_file_page_period_scope_used_for_mapping_or_routing"] is False
    assert evidence["authority"]["numeric_authority"] is False
    assert mapping["authority"]["new_schema_identity_creation_authority"] is False
