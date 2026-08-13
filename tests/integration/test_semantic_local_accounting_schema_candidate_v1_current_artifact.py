from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    build_semantic_local_accounting_schema_candidate_v1,
    validate_semantic_local_accounting_schema_candidate_replay_v1,
)
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    build_semantic_local_accounting_graph_v2,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    bind_vietocr_semantic_page_v2,
    validate_vietocr_semantic_receipt_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
MANIFEST = RUN_ROOT / "frozen/crop_manifest.json"
REQUEST = RUN_ROOT / "frozen/reader_request.json"
RESULT = RUN_ROOT / "outputs/vgg-transformer/ocr_result.json"
RUN = RUN_ROOT / "outputs/vgg-transformer/run_manifest.json"
TIER1 = Path("tests/fixtures/source_structure/local_accounting_graph_v1_tier1_cases.json")
RESULT_SHA256 = "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
RUN_SHA256 = "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"
SPECS = (
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
    LOAN_MATURITY_BUCKETS_SPEC_V1,
)


def _json(path: Path | str) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


def _hydrated() -> bool:
    return all((PROJECT_ROOT / path).is_file() for path in (MANIFEST, REQUEST, RESULT, RUN, TIER1))


@pytest.fixture(scope="module")
def real_inputs():
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run is not hydrated")
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=RESULT_SHA256,
        expected_run_manifest_sha256=RUN_SHA256,
    )
    page = _json(MANIFEST)["pages"][0]
    wanted = page["result_ref"]["sha256"]
    target = None
    for case in _json(TIER1)["cases"]:
        provenance = case["provenance_only_not_inference"]
        for candidate in provenance["page_inputs"]:
            result_ref = candidate["result_ref"]
            if result_ref is not None and result_ref["sha256"] == wanted:
                target = provenance, candidate
    assert target is not None
    provenance, candidate = target
    document = _json(provenance["v3_document_manifest_ref"]["path"])
    record_index = int(candidate["page_record_json_pointer"].removeprefix("/page_records/"))
    projection = project_authenticated_page_v2(
        page_record=document["page_records"][record_index],
        page_result=_json(candidate["result_ref"]["path"]),
    )
    binding = bind_vietocr_semantic_page_v2(projection, receipt)
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    return receipt, projection, binding, graph


def test_real_shb_graph_replays_to_candidate_only_tm_slice(real_inputs) -> None:
    receipt, projection, binding, graph = real_inputs
    result = build_semantic_local_accounting_schema_candidate_v1(
        PROJECT_ROOT,
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )

    assert (
        validate_semantic_local_accounting_schema_candidate_replay_v1(
            result,
            PROJECT_ROOT,
            graph,
            projection,
            binding,
            receipt,
            LOAN_MATURITY_BUCKETS_SPEC_V1,
            SPECS,
        )
        == result
    )
    assert graph["graph_id"] == (
        "slagv2:graph:47ec2635a8b57ee0773f26612d97dc7ce1a700993b169c25d7286f9b74be28d7"
    )
    assert result["status"] == "CANDIDATE_SET_READY"
    assert result["metrics"] == {
        "candidate_role_count": 6,
        "singleton_schema_candidate_count": 5,
        "source_only_validation_role_count": 1,
        "unassessed_schema_child_count": 1,
    }
    assert result["readiness"]["schema_mapping_ready"] is False
    assert result["readiness"]["export_eligible"] is False
