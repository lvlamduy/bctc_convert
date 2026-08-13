from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    build_semantic_local_accounting_graph_v2,
    validate_semantic_local_accounting_graph_replay_v2,
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
    required = [MANIFEST, REQUEST, RESULT, RUN, TIER1]
    if not all((PROJECT_ROOT / path).is_file() for path in required):
        return False
    run = _json(RUN)
    external_root = Path(run["runtime"]["external_root"])
    return all(
        (external_root / artifact["path"]).is_file()
        for artifact in run["runtime"]["artifacts"].values()
    )


@pytest.fixture(scope="module")
def real_inputs():
    if not _hydrated():
        pytest.skip("frozen five-page Transformer run or pinned runtime is not hydrated")
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=RESULT_SHA256,
        expected_run_manifest_sha256=RUN_SHA256,
    )
    fixture = _json(TIER1)
    manifest_pages = _json(MANIFEST)["pages"]
    wanted_hashes = {page["result_ref"]["sha256"] for page in manifest_pages}
    targets: dict[str, tuple[dict, dict]] = {}
    for case in fixture["cases"]:
        provenance = case["provenance_only_not_inference"]
        for page in provenance["page_inputs"]:
            reference = page["result_ref"]
            if reference is not None and reference["sha256"] in wanted_hashes:
                targets.setdefault(reference["sha256"], (provenance, page))
    pages = {}
    for opaque_page in manifest_pages:
        provenance, page = targets[opaque_page["result_ref"]["sha256"]]
        document_manifest = _json(provenance["v3_document_manifest_ref"]["path"])
        record_index = int(page["page_record_json_pointer"].removeprefix("/page_records/"))
        projection = project_authenticated_page_v2(
            page_record=document_manifest["page_records"][record_index],
            page_result=_json(page["result_ref"]["path"]),
        )
        pages[opaque_page["page_id"]] = (
            projection,
            bind_vietocr_semantic_page_v2(projection, receipt),
        )
    return receipt, pages


def _build(real_inputs, page_id: str, spec):
    receipt, pages = real_inputs
    projection, binding = pages[page_id]
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        spec,
        SPECS,
    )
    assert (
        validate_semantic_local_accounting_graph_replay_v2(
            graph,
            projection,
            binding,
            receipt,
            spec,
            SPECS,
        )
        == graph
    )
    return graph


def test_real_shb_page24_maturity_persists_one_closed_graph(real_inputs) -> None:
    graph = _build(real_inputs, "page-0001", LOAN_MATURITY_BUCKETS_SPEC_V1)

    assert graph["status"] == "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE"
    assert graph["metrics"] == {
        "accepted_region_count": 1,
        "node_count": 36,
        "edge_count": 81,
        "evidence_node_count": 17,
        "orphan_node_count": 0,
        "orphan_evidence_count": 0,
        "invalid_edge_count": 0,
        "disconnected_node_count": 0,
        "accepted_counts": {
            "TABLE": 1,
            "LOGICAL_ROW": 4,
            "VALUE_POSITION": 8,
            "AXIS": 2,
            "HIERARCHY": 12,
        },
    }
    rows = sorted(
        (node for node in graph["nodes"] if node["kind"] == "LOGICAL_ROW"),
        key=lambda node: node["attributes"]["ordinal"],
    )
    assert [node["attributes"]["row_role"] for node in rows] == [
        "SHORT_TERM",
        "MEDIUM_TERM",
        "LONG_TERM",
        "TOTAL",
    ]
    assert graph["arithmetic"] == {
        "status": "CORROBORATED",
        "evaluated_axis_indexes": [0, 1],
        "internal_additive_closure_only": True,
        "same_population_claimed": False,
    }
    assert graph["supplied_family_evaluation_partition"] == {
        "LOAN_MATURITY_BUCKETS": {
            "use": "TARGET_FAMILY_EVALUATED",
            "disposition": "ACCEPTED_WITHIN_SUPPLIED_FAMILY_COLLISION_SCOPE",
        },
        "LOAN_QUALITY_CLASSIFICATION": {
            "use": "COLLISION_SCOPE_ONLY",
            "disposition": "NOT_EVALUATED",
        },
    }
    assert graph["safety"]["canonicalization_authority"] is False
    assert graph["safety"]["schema_mapping_authority"] is False
    assert graph["safety"]["export_authority"] is False


@pytest.mark.parametrize(
    ("page_id", "spec"),
    (
        ("page-0003", LOAN_QUALITY_CLASSIFICATION_SPEC_V1),
        ("page-0004", LOAN_QUALITY_CLASSIFICATION_SPEC_V1),
        ("page-0005", LOAN_MATURITY_BUCKETS_SPEC_V1),
    ),
)
def test_real_controls_persist_zero_accepted_topology(real_inputs, page_id, spec) -> None:
    graph = _build(real_inputs, page_id, spec)

    assert graph["status"] == "UNRESOLVED"
    assert graph["nodes"] == []
    assert graph["edges"] == []
    assert graph["metrics"] == {
        "accepted_region_count": 0,
        "node_count": 0,
        "edge_count": 0,
        "evidence_node_count": 0,
        "orphan_node_count": 0,
        "orphan_evidence_count": 0,
        "invalid_edge_count": 0,
        "disconnected_node_count": 0,
        "accepted_counts": {
            "TABLE": 0,
            "LOGICAL_ROW": 0,
            "VALUE_POSITION": 0,
            "AXIS": 0,
            "HIERARCHY": 0,
        },
    }
    assert graph["acceptance_scope"]["ready_within_supplied_family_collision_scope"] is False
