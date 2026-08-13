from __future__ import annotations

import sys
from pathlib import Path

from bctc_ai.source_structure import local_accounting_typed_proposals_v1 as typed
from bctc_ai.source_structure.contracts_v2 import (
    validate_source_evidence_projection_v2,
)
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)

INTEGRATION_TEST_ROOT = Path(__file__).resolve().parent
if str(INTEGRATION_TEST_ROOT) not in sys.path:
    sys.path.insert(0, str(INTEGRATION_TEST_ROOT))

from test_local_accounting_graph_v1_exact_v2 import (  # noqa: E402
    _exact_quality_ocr_projection,
)


def test_exact_ocr_v2_projection_emits_replayable_quality_semantics_and_topology() -> None:
    projection = _exact_quality_ocr_projection(owner_text="Cho vay khách hàng")
    assert validate_source_evidence_projection_v2(projection) == projection

    artifact = typed.build_local_accounting_typed_proposal_set_v1(
        projection,
        (LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
    )

    assert (
        typed.validate_local_accounting_typed_proposal_set_v1(
            artifact,
            source_projection_v2=projection,
            family_specs=(LOAN_QUALITY_CLASSIFICATION_SPEC_V1,),
        )
        == artifact
    )
    assert artifact["source_binding"]["source_route"] == "DOMINANT_RASTER_OCR"
    assert artifact["metrics"]["source_line_scan_passes"] == 1
    assert artifact["metrics"]["eligible_primary_line_count"] == 23
    assert artifact["metrics"]["exact_semantic_line_proposal_count"] == 8
    assert artifact["metrics"]["topology_candidate_count"] == 1
    assert artifact["metrics"]["exact_ordered_topology_candidate_count"] == 1

    proposal_by_id = {
        item["semantic_proposal_id"]: item for item in artifact["semantic_line_proposals"]
    }
    candidate = artifact["topology_candidates"][0]
    assert candidate["candidate_status"] == "EXACT_ORDERED_STRUCTURE_CANDIDATE"
    assert candidate["missing_required_roles"] == []
    assert candidate["repeated_required_roles"] == []
    assert candidate["orphan_branch"] is False
    assert candidate["order_conflict"] is False
    assert {(item["role_kind"], item["role"]) for item in candidate["member_role_candidates"]} == {
        ("OWNER", "OWNER"),
        ("BRANCH", "BRANCH"),
        ("ORDERED_CHILD", "STANDARD"),
        ("ORDERED_CHILD", "SPECIAL_MENTION"),
        ("ORDERED_CHILD", "SUBSTANDARD"),
        ("ORDERED_CHILD", "DOUBTFUL"),
        ("ORDERED_CHILD", "LOSS"),
        ("TOTAL", "TOTAL"),
    }
    exact_source_ids = {
        atom["source_local_id"]
        for atom in projection["neutral_page_v1"]["atoms"]
        if atom["kind"] == "LINE" and atom["authority"] == "AUTHENTICATED_PRIMARY"
    }
    assert {
        proposal_by_id[proposal_id]["raw_span"]["source_atom_id"]
        for proposal_id in candidate["semantic_proposal_ids"]
    }.issubset(exact_source_ids)
    assert artifact["topology_dispositions"] == [
        {
            "topology_candidate_id": candidate["topology_candidate_id"],
            "disposition": "RETAINED_FOR_BOUNDED_OBSERVATION_ASSEMBLY",
            "reason_code": "COMPLETE_EXACT_ORDERED_FAMILY_VOCABULARY",
        }
    ]
    assert artifact["safety"]["lag_observation_assembled"] is False
    assert artifact["safety"]["semantic_acceptance_claimed"] is False
