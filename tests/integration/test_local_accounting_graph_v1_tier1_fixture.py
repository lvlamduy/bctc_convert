from __future__ import annotations

import json
from collections import Counter
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    PROJECT_ROOT / "tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json"
)
EXPECTED_TOP_LEVEL_FIELDS = {
    "cases",
    "claim_boundary",
    "evidence_scope",
    "format_version",
    "frozen_research_authorities",
    "inference_firewall",
    "purpose",
}
EXPECTED_CASE_FIELDS = {
    "evaluation_metadata",
    "inference_payload",
    "provenance_only_not_inference",
}
EXPECTED_INFERENCE_FIELDS = {
    "family",
    "candidate_source_atom_ids_by_observable_role",
}
EXPECTED_DISPOSITIONS = Counter({"REJECT": 16, "ACCEPT": 11, "UNRESOLVED": 2})
EXPECTED_FAMILIES = Counter({"LOAN_MATURITY_BUCKETS": 15, "LOAN_QUALITY_CLASSIFICATION": 14})


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_bytes())


def _repo_path(relative_path: str) -> Path:
    path = Path(relative_path)
    assert not path.is_absolute()
    resolved = (PROJECT_ROOT / path).resolve()
    assert resolved.is_relative_to(PROJECT_ROOT.resolve())
    return resolved


def _assert_object_ref(reference: dict) -> bytes:
    assert set(reference) == {"path", "sha256", "size_bytes"}
    payload = _repo_path(reference["path"]).read_bytes()
    assert len(payload) == reference["size_bytes"]
    assert sha256(payload).hexdigest() == reference["sha256"]
    return payload


def _page_record(manifest: dict, pointer: str) -> dict:
    prefix = "/page_records/"
    assert pointer.startswith(prefix)
    index_text = pointer.removeprefix(prefix)
    assert index_text.isdigit()
    return manifest["page_records"][int(index_text)]


def test_tier1_fixture_keeps_evaluation_provenance_out_of_inference_payload() -> None:
    fixture = _fixture()
    assert set(fixture) == EXPECTED_TOP_LEVEL_FIELDS
    assert (
        fixture["format_version"]
        == "GENERIC_LOCAL_ACCOUNTING_GRAPH_V1_TIER1_DEVELOPMENT_REPLAY_FIXTURE_V1"
    )
    assert fixture["claim_boundary"].startswith("DEVELOPMENT_REPLAY_ONLY")

    cases = fixture["cases"]
    assert len(cases) == 29
    fixture_ids = [case["evaluation_metadata"]["fixture_id"] for case in cases]
    assert len(set(fixture_ids)) == len(fixture_ids)
    assert (
        Counter(case["evaluation_metadata"]["expected_disposition"] for case in cases)
        == EXPECTED_DISPOSITIONS
    )
    assert Counter(case["evaluation_metadata"]["family"] for case in cases) == EXPECTED_FAMILIES
    assert fixture["evidence_scope"]["expected_disposition_counts"] == dict(EXPECTED_DISPOSITIONS)
    assert fixture["evidence_scope"]["family_counts"] == dict(EXPECTED_FAMILIES)
    assert fixture["evidence_scope"]["freshness"] == "DEVELOPMENT_REPLAY"
    coverage = fixture["evidence_scope"]["family_coverage_board_denominators"]
    assert coverage["scope"] == "TIER1_DEVELOPMENT_REPLAY_PANEL_ONLY__NOT_WAVE1_DENOMINATOR"
    assert coverage["acceptance_measurement_status"] == ("NOT_MEASURED__LAG_V1_RUNNER_REQUIRED")
    assert coverage["families"] == {
        "LOAN_MATURITY_BUCKETS": {
            "banks_inspected_count": 8,
            "case_count": 15,
            "expected_strict_accept_bank_count": 5,
            "expected_strict_accept_case_count": 5,
            "expected_unresolved_bank_count": 0,
            "expected_unresolved_case_count": 0,
            "measured_accepted_bank_count": None,
            "negative_control_bank_count": 7,
            "negative_control_case_count": 10,
            "source_occurrence_bank_count": 5,
            "source_occurrence_case_count": 5,
        },
        "LOAN_QUALITY_CLASSIFICATION": {
            "banks_inspected_count": 8,
            "case_count": 14,
            "expected_strict_accept_bank_count": 6,
            "expected_strict_accept_case_count": 6,
            "expected_unresolved_bank_count": 2,
            "expected_unresolved_case_count": 2,
            "measured_accepted_bank_count": None,
            "negative_control_bank_count": 5,
            "negative_control_case_count": 6,
            "source_occurrence_bank_count": 8,
            "source_occurrence_case_count": 8,
        },
    }

    for case in cases:
        assert set(case) == EXPECTED_CASE_FIELDS
        metadata = case["evaluation_metadata"]
        payload = case["inference_payload"]
        provenance = case["provenance_only_not_inference"]
        assert set(payload) == EXPECTED_INFERENCE_FIELDS
        assert payload["family"] == metadata["family"]
        assert {
            "bank",
            "document_id",
            "physical_page",
            "source_pdf_ref",
            "v3_document_manifest_ref",
            "page_inputs",
        } == set(provenance)
        assert not ({"bank", "document_id", "filename", "physical_page"} & set(payload))
        if metadata["source_truth"] == "NEGATIVE_CONTROL":
            assert metadata["expected_disposition"] == "REJECT"
            assert metadata["control_archetype"]
        else:
            assert metadata["source_truth"] == "POSITIVE_SOURCE_FAMILY"
            assert metadata["expected_disposition"] in {"ACCEPT", "UNRESOLVED"}
            assert metadata["control_archetype"] is None

        page_projection_ids = {
            page["source_projection"]["identity"] for page in provenance["page_inputs"]
        }
        assert [page["relation"] for page in provenance["page_inputs"]] == [
            "PREVIOUS",
            "TARGET",
            "NEXT",
        ]
        for page in provenance["page_inputs"]:
            if page["render_ref"] is None:
                assert page["route"] == "CAUSAL_NATIVE_TEXT"
            else:
                assert page["route"] == "DOMINANT_RASTER_OCR"
        for role, groups in payload["candidate_source_atom_ids_by_observable_role"].items():
            assert role == role.upper()
            assert set(groups) <= page_projection_ids
            for atom_ids in groups.values():
                assert len(atom_ids) == len(set(atom_ids))
                assert all(atom_id.startswith("ssv1:atom:") for atom_id in atom_ids)


def test_tier1_fixture_reconstructs_exact_v2_projections_and_atom_refs() -> None:
    fixture = _fixture()
    all_references: dict[str, dict] = {}
    manifest_payloads: dict[str, dict] = {}

    for authority_name in (
        "source_profile",
        "source_first_inventory",
        "compact_prestructural_graph_inventory",
    ):
        authority = fixture["frozen_research_authorities"][authority_name]
        all_references.setdefault(
            authority["path"],
            {key: authority[key] for key in ("path", "sha256", "size_bytes")},
        )
    for case in fixture["cases"]:
        provenance = case["provenance_only_not_inference"]
        for reference in (
            provenance["source_pdf_ref"],
            provenance["v3_document_manifest_ref"],
        ):
            all_references.setdefault(reference["path"], reference)
        for page in provenance["page_inputs"]:
            for field in ("result_ref", "render_ref", "backend_payload_ref"):
                reference = page[field]
                if reference is not None:
                    all_references.setdefault(reference["path"], reference)

    missing = [path for path in all_references if not _repo_path(path).is_file()]
    if missing:
        pytest.skip(f"frozen V3 Tier-1 evidence is not hydrated: {missing[0]}")
    for reference in all_references.values():
        _assert_object_ref(reference)

    projections: dict[str, dict] = {}
    v3_root = _repo_path(fixture["frozen_research_authorities"]["v3_root"])
    for case in fixture["cases"]:
        provenance = case["provenance_only_not_inference"]
        manifest_ref = provenance["v3_document_manifest_ref"]
        if manifest_ref["path"] not in manifest_payloads:
            manifest_payloads[manifest_ref["path"]] = json.loads(
                _repo_path(manifest_ref["path"]).read_bytes()
            )
        manifest = manifest_payloads[manifest_ref["path"]]

        for page in provenance["page_inputs"]:
            projection_identity = page["source_projection"]["identity"]
            record = _page_record(manifest, page["page_record_json_pointer"])
            assert record["route"] == page["route"]
            assert record["status"] == page["status"]
            for field in ("result_ref", "render_ref", "backend_payload_ref"):
                fixture_ref = page[field]
                if fixture_ref is None:
                    assert record[field] is None
                    continue
                expected_relative_path = _repo_path(fixture_ref["path"]).relative_to(v3_root)
                assert record[field] == {
                    "path": expected_relative_path.as_posix(),
                    "sha256": fixture_ref["sha256"],
                    "size_bytes": fixture_ref["size_bytes"],
                }

            if projection_identity not in projections:
                result = json.loads(_repo_path(page["result_ref"]["path"]).read_bytes())
                projection = project_authenticated_page_v2(
                    page_record=record,
                    page_result=result,
                )
                assert projection["source_local_page_id"] == projection_identity
                assert canonical_json_sha256_v1(projection) == page["source_projection"]["sha256"]
                projections[projection_identity] = projection

    atom_maps = {
        projection_identity: {
            atom["source_local_id"]: (ordinal, atom)
            for ordinal, atom in enumerate(projection["neutral_page_v1"]["atoms"])
        }
        for projection_identity, projection in projections.items()
    }
    referenced_atom_count = 0
    for case in fixture["cases"]:
        groups_by_role = case["inference_payload"]["candidate_source_atom_ids_by_observable_role"]
        for groups in groups_by_role.values():
            for projection_identity, atom_ids in groups.items():
                atom_map = atom_maps[projection_identity]
                source_ordinals = [atom_map[atom_id][0] for atom_id in atom_ids]
                assert source_ordinals == sorted(source_ordinals)
                for atom_id in atom_ids:
                    referenced_atom_count += 1
                    assert atom_id in atom_map
                    assert atom_map[atom_id][1]["kind"] == "LINE"

    assert len(projections) == 75
    assert referenced_atom_count == 3_361
