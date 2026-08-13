from __future__ import annotations

import gc
import json
from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

import pytest

from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.evidence_projection_v2 import (
    project_authenticated_page_v2,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.local_accounting_typed_proposals_v1 import (
    build_local_accounting_typed_proposal_set_from_registry_v1,
    compile_local_accounting_typed_proposal_registry_v1,
    validate_local_accounting_typed_proposal_set_from_registry_v1,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_PATH = (
    PROJECT_ROOT / "tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json"
)
FAMILY_SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)

# These are measured proposal-seam results from the exact frozen TARGET pages.
# They are deliberately not expected LAG dispositions or accepted structures.
EXPECTED_MEASURED_PROPOSAL_SUMMARY = {
    "claim_boundary": ("TYPED_PROPOSAL_COVERAGE_ONLY__NO_LAG_OBSERVATION__NO_ACCEPTED_STRUCTURE"),
    "target_count": 29,
    "target_family_measurement_count": 58,
    "source_route_counts": {
        "CAUSAL_NATIVE_TEXT": 3,
        "DOMINANT_RASTER_OCR": 26,
    },
    "artifact_metric_totals": {
        "registry_compile_passes_on_page": 0,
        "bounded_edit_distance_evaluation_count": 102,
        "eligible_primary_line_count": 2_681,
        "exact_ordered_topology_candidate_count": 0,
        "exact_semantic_line_proposal_count": 33,
        "family_line_cartesian_evaluation_count": 0,
        "fuzzy_alias_fanout_overflow_line_count": 0,
        "fuzzy_index_posting_overflow_line_count": 0,
        "fuzzy_index_posting_visit_count": 71_573,
        "maximum_fuzzy_alias_candidate_fanout": 41,
        "source_line_scan_passes": 29,
        "total_fuzzy_alias_candidate_fanout": 100,
        "topology_candidate_count": 9,
        "topology_event_visit_count": 91,
        "unresolved_repair_line_proposal_count": 41,
        "unresolved_topology_candidate_count": 9,
    },
    "families": {
        "LOAN_MATURITY_BUCKETS": {
            "exact_semantic_proposal_count": 32,
            "repair_semantic_proposal_count": 15,
            "target_count": 29,
            "targets_with_exact_semantic_proposal": 16,
            "targets_with_repair_semantic_proposal": 11,
            "targets_with_topology_candidate": 6,
            "topology_candidate_count": 6,
            "topology_status_counts": {
                "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE": 1,
                "UNRESOLVED_REPAIR_TOPOLOGY_CANDIDATE": 5,
            },
        },
        "LOAN_QUALITY_CLASSIFICATION": {
            "exact_semantic_proposal_count": 32,
            "repair_semantic_proposal_count": 31,
            "target_count": 29,
            "targets_with_exact_semantic_proposal": 16,
            "targets_with_repair_semantic_proposal": 14,
            "targets_with_topology_candidate": 3,
            "topology_candidate_count": 3,
            "topology_status_counts": {
                "UNRESOLVED_REPAIR_TOPOLOGY_CANDIDATE": 3,
            },
        },
    },
    "target_family_measurement_sha256": (
        "b67ab830f8393fef8637ffc7562581768da5edf600bf4cdc53912e764fbcca54"
    ),
}

EXPECTED_POST_FREEZE_DIAGNOSTIC = {
    "ACCEPT": {
        "case_count": 11,
        "exact_semantic_proposal_count": 15,
        "repair_semantic_proposal_count": 14,
        "targets_with_exact_semantic_proposal": 9,
        "targets_with_repair_semantic_proposal": 8,
        "targets_with_topology_candidate": 4,
        "topology_candidate_count": 4,
        "topology_status_counts": {
            "UNRESOLVED_INCOMPLETE_OR_AMBIGUOUS_TOPOLOGY_CANDIDATE": 1,
            "UNRESOLVED_REPAIR_TOPOLOGY_CANDIDATE": 3,
        },
    },
    "REJECT": {
        "case_count": 16,
        "exact_semantic_proposal_count": 12,
        "repair_semantic_proposal_count": 9,
        "targets_with_exact_semantic_proposal": 5,
        "targets_with_repair_semantic_proposal": 5,
        "targets_with_topology_candidate": 0,
        "topology_candidate_count": 0,
        "topology_status_counts": {},
    },
    "UNRESOLVED": {
        "case_count": 2,
        "exact_semantic_proposal_count": 5,
        "repair_semantic_proposal_count": 5,
        "targets_with_exact_semantic_proposal": 2,
        "targets_with_repair_semantic_proposal": 2,
        "targets_with_topology_candidate": 0,
        "topology_candidate_count": 0,
        "topology_status_counts": {},
    },
}


@dataclass(frozen=True)
class _TargetSourceJob:
    case_ordinal: int
    manifest_path: str
    manifest_sha256: str
    manifest_size_bytes: int
    page_record_json_pointer: str
    result_path: str
    result_sha256: str
    result_size_bytes: int
    expected_projection_identity: str
    expected_projection_sha256: str
    expected_route: str


@dataclass(frozen=True)
class _FamilyMeasurement:
    case_ordinal: int
    source_route: str
    family_id: str
    exact_semantic_proposal_count: int
    repair_semantic_proposal_count: int
    topology_candidate_count: int
    topology_status_counts: tuple[tuple[str, int], ...]


@dataclass(frozen=True)
class _TargetMeasurement:
    case_ordinal: int
    source_route: str
    artifact_metrics: tuple[tuple[str, int], ...]
    families: tuple[_FamilyMeasurement, ...]


def _fixture() -> dict:
    return json.loads(FIXTURE_PATH.read_bytes())


def _repo_path(relative_path: str) -> Path:
    path = Path(relative_path)
    assert not path.is_absolute()
    resolved = (PROJECT_ROOT / path).resolve()
    assert resolved.is_relative_to(PROJECT_ROOT.resolve())
    return resolved


def _target_jobs(fixture: dict) -> tuple[_TargetSourceJob, ...]:
    """Select source inputs without exposing labels or role-group candidates."""

    jobs: list[_TargetSourceJob] = []
    for case_ordinal, case in enumerate(fixture["cases"]):
        provenance = case["provenance_only_not_inference"]
        manifest = provenance["v3_document_manifest_ref"]
        target = next(page for page in provenance["page_inputs"] if page["relation"] == "TARGET")
        result = target["result_ref"]
        jobs.append(
            _TargetSourceJob(
                case_ordinal=case_ordinal,
                manifest_path=manifest["path"],
                manifest_sha256=manifest["sha256"],
                manifest_size_bytes=manifest["size_bytes"],
                page_record_json_pointer=target["page_record_json_pointer"],
                result_path=result["path"],
                result_sha256=result["sha256"],
                result_size_bytes=result["size_bytes"],
                expected_projection_identity=target["source_projection"]["identity"],
                expected_projection_sha256=target["source_projection"]["sha256"],
                expected_route=target["route"],
            )
        )
    return tuple(jobs)


def _read_bound_json(path: str, expected_sha256: str, expected_size: int) -> dict:
    payload = _repo_path(path).read_bytes()
    assert len(payload) == expected_size
    assert sha256(payload).hexdigest() == expected_sha256
    return json.loads(payload)


def _page_record(manifest: dict, pointer: str) -> dict:
    prefix = "/page_records/"
    assert pointer.startswith(prefix)
    index_text = pointer.removeprefix(prefix)
    assert index_text.isdigit()
    return manifest["page_records"][int(index_text)]


def _family_measurement(
    *,
    case_ordinal: int,
    source_route: str,
    artifact: dict,
    family_id: str,
) -> _FamilyMeasurement:
    exact_ids: set[str] = set()
    repair_ids: set[str] = set()
    for proposal in artifact["semantic_line_proposals"]:
        matches = [
            match for match in proposal["candidate_matches"] if match["family_id"] == family_id
        ]
        if any(match["match_kind"] == "EXACT_ALIAS" for match in matches):
            exact_ids.add(proposal["semantic_proposal_id"])
        if any(match["match_kind"] == "BOUNDED_EDIT_CANDIDATE" for match in matches):
            repair_ids.add(proposal["semantic_proposal_id"])

    topology = [
        candidate
        for candidate in artifact["topology_candidates"]
        if candidate["family_id"] == family_id
    ]
    return _FamilyMeasurement(
        case_ordinal=case_ordinal,
        source_route=source_route,
        family_id=family_id,
        exact_semantic_proposal_count=len(exact_ids),
        repair_semantic_proposal_count=len(repair_ids),
        topology_candidate_count=len(topology),
        topology_status_counts=tuple(
            sorted(Counter(item["candidate_status"] for item in topology).items())
        ),
    )


def _run_typed_proposal_sweep(
    jobs: tuple[_TargetSourceJob, ...],
) -> tuple[_TargetMeasurement, ...]:
    manifests: dict[str, dict] = {}
    compiled_registry = compile_local_accounting_typed_proposal_registry_v1(FAMILY_SPECS)
    measured: list[_TargetMeasurement] = []
    metric_fields = tuple(EXPECTED_MEASURED_PROPOSAL_SUMMARY["artifact_metric_totals"])

    for job in jobs:
        if job.manifest_path not in manifests:
            manifests[job.manifest_path] = _read_bound_json(
                job.manifest_path,
                job.manifest_sha256,
                job.manifest_size_bytes,
            )
        record = _page_record(manifests[job.manifest_path], job.page_record_json_pointer)
        result = _read_bound_json(
            job.result_path,
            job.result_sha256,
            job.result_size_bytes,
        )
        assert record["route"] == job.expected_route
        projection = project_authenticated_page_v2(
            page_record=record,
            page_result=result,
        )
        assert projection["source_local_page_id"] == job.expected_projection_identity
        assert canonical_json_sha256_v1(projection) == job.expected_projection_sha256

        # No evaluation label, broad candidate-role group, bank, page, or schema
        # field is passed to this candidate-only generator.
        artifact = build_local_accounting_typed_proposal_set_from_registry_v1(
            projection, compiled_registry
        )
        replayed = validate_local_accounting_typed_proposal_set_from_registry_v1(
            artifact,
            source_projection_v2=projection,
            compiled_registry=compiled_registry,
        )
        assert replayed == artifact
        assert artifact["metrics"]["source_line_scan_passes"] == 1
        assert artifact["metrics"]["registry_compile_passes_on_page"] == 0
        assert artifact["metrics"]["family_line_cartesian_evaluation_count"] == 0
        assert (
            artifact["metrics"]["eligible_primary_line_visit_count"]
            == artifact["metrics"]["eligible_primary_line_count"]
        )
        assert artifact["safety"]["lag_core_invoked"] is False
        assert artifact["safety"]["lag_observation_assembled"] is False
        assert artifact["safety"]["semantic_acceptance_claimed"] is False

        measured.append(
            _TargetMeasurement(
                case_ordinal=job.case_ordinal,
                source_route=projection["route"],
                artifact_metrics=tuple(
                    (field, artifact["metrics"][field]) for field in metric_fields
                ),
                families=tuple(
                    _family_measurement(
                        case_ordinal=job.case_ordinal,
                        source_route=projection["route"],
                        artifact=artifact,
                        family_id=spec.family_id,
                    )
                    for spec in FAMILY_SPECS
                ),
            )
        )

        # V3 page results can be large.  Measurements above contain only frozen
        # counters, never source payloads or evaluation metadata.
        del replayed, artifact, projection, result
        gc.collect()

    return tuple(measured)


def _measurement_rows(
    measurements: tuple[_TargetMeasurement, ...],
) -> list[dict]:
    return [
        {
            "case_ordinal": family.case_ordinal,
            "source_route": family.source_route,
            "family_id": family.family_id,
            "exact_semantic_proposal_count": family.exact_semantic_proposal_count,
            "repair_semantic_proposal_count": family.repair_semantic_proposal_count,
            "topology_candidate_count": family.topology_candidate_count,
            "topology_status_counts": dict(family.topology_status_counts),
        }
        for target in measurements
        for family in target.families
    ]


def _measured_summary(
    measurements: tuple[_TargetMeasurement, ...],
) -> dict:
    rows = _measurement_rows(measurements)
    metric_totals: Counter[str] = Counter()
    for target in measurements:
        metric_totals.update(dict(target.artifact_metrics))

    family_summaries: dict[str, dict] = {}
    for family_id in sorted(spec.family_id for spec in FAMILY_SPECS):
        family_rows = [row for row in rows if row["family_id"] == family_id]
        statuses: Counter[str] = Counter()
        for row in family_rows:
            statuses.update(row["topology_status_counts"])
        family_summaries[family_id] = {
            "exact_semantic_proposal_count": sum(
                row["exact_semantic_proposal_count"] for row in family_rows
            ),
            "repair_semantic_proposal_count": sum(
                row["repair_semantic_proposal_count"] for row in family_rows
            ),
            "target_count": len(family_rows),
            "targets_with_exact_semantic_proposal": sum(
                row["exact_semantic_proposal_count"] > 0 for row in family_rows
            ),
            "targets_with_repair_semantic_proposal": sum(
                row["repair_semantic_proposal_count"] > 0 for row in family_rows
            ),
            "targets_with_topology_candidate": sum(
                row["topology_candidate_count"] > 0 for row in family_rows
            ),
            "topology_candidate_count": sum(row["topology_candidate_count"] for row in family_rows),
            "topology_status_counts": dict(sorted(statuses.items())),
        }

    return {
        "claim_boundary": (
            "TYPED_PROPOSAL_COVERAGE_ONLY__NO_LAG_OBSERVATION__NO_ACCEPTED_STRUCTURE"
        ),
        "target_count": len(measurements),
        "target_family_measurement_count": len(rows),
        "source_route_counts": dict(
            sorted(Counter(item.source_route for item in measurements).items())
        ),
        "artifact_metric_totals": dict(sorted(metric_totals.items())),
        "families": family_summaries,
        "target_family_measurement_sha256": canonical_json_sha256_v1(rows),
    }


def _post_freeze_diagnostic(
    measurements: tuple[_TargetMeasurement, ...],
    fixture: dict,
) -> dict:
    """Join evaluation labels only after source-only measurements are frozen."""

    by_case_and_family = {
        (family.case_ordinal, family.family_id): family
        for target in measurements
        for family in target.families
    }
    grouped: dict[str, list[_FamilyMeasurement]] = {}
    for case_ordinal, case in enumerate(fixture["cases"]):
        metadata = case["evaluation_metadata"]
        grouped.setdefault(metadata["expected_disposition"], []).append(
            by_case_and_family[(case_ordinal, metadata["family"])]
        )

    diagnostic: dict[str, dict] = {}
    for disposition, items in sorted(grouped.items()):
        statuses: Counter[str] = Counter()
        for item in items:
            statuses.update(dict(item.topology_status_counts))
        diagnostic[disposition] = {
            "case_count": len(items),
            "exact_semantic_proposal_count": sum(
                item.exact_semantic_proposal_count for item in items
            ),
            "repair_semantic_proposal_count": sum(
                item.repair_semantic_proposal_count for item in items
            ),
            "targets_with_exact_semantic_proposal": sum(
                item.exact_semantic_proposal_count > 0 for item in items
            ),
            "targets_with_repair_semantic_proposal": sum(
                item.repair_semantic_proposal_count > 0 for item in items
            ),
            "targets_with_topology_candidate": sum(
                item.topology_candidate_count > 0 for item in items
            ),
            "topology_candidate_count": sum(item.topology_candidate_count for item in items),
            "topology_status_counts": dict(sorted(statuses.items())),
        }
    return diagnostic


def test_tier1_exact_target_typed_proposal_coverage_and_post_freeze_diagnostic() -> None:
    fixture = _fixture()
    jobs = _target_jobs(fixture)
    missing = [
        path
        for job in jobs
        for path in (job.manifest_path, job.result_path)
        if not _repo_path(path).is_file()
    ]
    if missing:
        pytest.skip(f"frozen V3 Tier-1 evidence is not hydrated: {missing[0]}")

    # Source-only proposal output is computed and frozen before this test reads
    # any evaluation label.  Both family specs run on every exact TARGET page.
    measurements = _run_typed_proposal_sweep(jobs)
    assert _measured_summary(measurements) == EXPECTED_MEASURED_PROPOSAL_SUMMARY

    # Diagnostic labels are joined only now; they never route proposal inference.
    diagnostic = _post_freeze_diagnostic(measurements, fixture)
    assert diagnostic == EXPECTED_POST_FREEZE_DIAGNOSTIC
    assert diagnostic["REJECT"]["topology_candidate_count"] == 0
    assert (
        sum(
            item["topology_status_counts"].get("EXACT_ORDERED_STRUCTURE_CANDIDATE", 0)
            for item in diagnostic.values()
        )
        == 0
    )
