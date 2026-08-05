from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta

import pytest
import yaml

from bctc_ai.core.hashing import sha256_file
from bctc_ai.evaluation.frozen_suite import (
    EvidenceItem,
    EvidenceKind,
    EvidenceStage,
    FrozenSuiteError,
    load_frozen_suite,
    validate_evidence_manifest,
)


def _write_jsonl(path, records):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(record) + "\n" for record in records))


def _suite(tmp_path):
    left = tmp_path / "left.pdf"
    right = tmp_path / "right.pdf"
    left.write_bytes(b"%PDF-left")
    right.write_bytes(b"%PDF-right")
    assigned = datetime.now(UTC)
    sources = []
    roles = []
    for _fixture_id, path, _fixture_role in (
        ("left", left, "ROLE_A_SOURCE"),
        ("right", right, "ROLE_B_SOURCE"),
    ):
        digest = sha256_file(path)
        sources.append(
            {
                "relative_path": path.name,
                "sha256": digest,
            }
        )
        roles.append(
            {
                "document_id": f"sha256:{digest}",
                "dataset_role": "CALIBRATION",
                "source_path": path.name,
                "assigned_at": assigned.isoformat(),
            }
        )
    _write_jsonl(tmp_path / "data/registered/source_registry.jsonl", sources)
    _write_jsonl(tmp_path / "data/registered/dataset_roles.jsonl", roles)
    payload = {
        "version": 1,
        "suite_id": "test-suite",
        "experiment_id": "E-TEST",
        "dataset_role": "CALIBRATION",
        "frozen_at": (assigned + timedelta(seconds=1)).isoformat(),
        "content_inspected_before_role_assignment": False,
        "sources": [
            {
                "fixture_id": fixture_id,
                "bank": "TEST",
                "fixture_role": fixture_role,
                "path": path.name,
                "sha256": sha256_file(path),
            }
            for fixture_id, path, fixture_role in (
                ("left", left, "ROLE_A_SOURCE"),
                ("right", right, "ROLE_B_SOURCE"),
            )
        ],
        "pairing": {
            "reference_fixture_id": "left",
            "candidate_fixture_id": "right",
            "target_reference_pages": [1],
            "target_page_contracts": [
                {
                    "reference_page": 1,
                    "candidate_page": 2,
                    "statement_type": "CDKT",
                    "expected_scope": "MAIN_STATEMENT",
                }
            ],
        },
        "evidence_policy": {
            "role_b_can_read_role_a_source": False,
            "role_b_can_read_role_a_result": False,
            "compare_starts_after_role_b_complete": True,
            "page_pairing_uses_text_or_values": False,
        },
        "historical_policy": {
            "lookup_stage": "POST_SCHEMA_RESOLUTION_ONLY",
            "lookup_requires_resolved_id": True,
            "mapping_candidate_generation": False,
            "pdf_confidence_promotion": False,
            "pdf_value_overwrite": False,
            "pdf_ytd_operand": False,
        },
    }
    config = tmp_path / "suite.yaml"
    config.write_text(yaml.safe_dump(payload))
    return config, payload


def test_frozen_suite_requires_preinspection_role_and_registered_hash(tmp_path):
    config, _payload = _suite(tmp_path)

    suite = load_frozen_suite(tmp_path, config)

    assert suite.dataset_role.value == "CALIBRATION"
    assert suite.source("left").fixture_role == "ROLE_A_SOURCE"


def test_frozen_suite_rejects_role_assignment_after_freeze(tmp_path):
    config, payload = _suite(tmp_path)
    payload["frozen_at"] = "2000-01-01T00:00:00+00:00"
    config.write_text(yaml.safe_dump(payload))

    with pytest.raises(FrozenSuiteError, match="assigned after suite freeze"):
        load_frozen_suite(tmp_path, config)


def test_role_b_mapping_rejects_reference_and_historical_evidence():
    with pytest.raises(FrozenSuiteError, match="forbidden"):
        validate_evidence_manifest(
            EvidenceStage.ROLE_B_MAPPING,
            (EvidenceItem(EvidenceKind.ROLE_A_RESULT, "machine_reference.jsonl"),),
        )
    with pytest.raises(FrozenSuiteError, match="forbidden"):
        validate_evidence_manifest(
            EvidenceStage.ROLE_B_MAPPING,
            (
                EvidenceItem(
                    EvidenceKind.HISTORICAL_WEAK_REFERENCE,
                    "data/local/historical_weak_reference.duckdb",
                ),
            ),
        )


def test_history_is_allowed_only_for_post_mapping_validation():
    validate_evidence_manifest(
        EvidenceStage.ROLE_B_POST_MAPPING_VALIDATION,
        (
            EvidenceItem(EvidenceKind.ROLE_B_RESULT, "pipeline_results.jsonl"),
            EvidenceItem(
                EvidenceKind.HISTORICAL_WEAK_REFERENCE,
                "data/local/historical_weak_reference.duckdb",
            ),
        ),
    )
