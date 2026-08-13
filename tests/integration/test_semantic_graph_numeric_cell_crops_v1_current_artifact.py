from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest

from bctc_ai.evaluation.semantic_graph_numeric_cell_crops_v1 import (
    build_semantic_graph_numeric_cell_crop_registry_v1,
    validate_semantic_graph_numeric_cell_crop_registry_replay_v1,
)
from bctc_ai.ocr.numeric_cell_reader import load_reference_blind_numeric_request
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


@pytest.fixture(scope="module")
def real_graph():
    if not all((PROJECT_ROOT / path).is_file() for path in (MANIFEST, REQUEST, RESULT, RUN, TIER1)):
        pytest.skip("frozen Transformer run is not hydrated")
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
    target = None
    for case in _json(TIER1)["cases"]:
        provenance = case["provenance_only_not_inference"]
        for candidate in provenance["page_inputs"]:
            reference = candidate["result_ref"]
            if reference is not None and reference["sha256"] == page["result_ref"]["sha256"]:
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


def test_real_shb_graph_yields_exact_eight_isolated_numeric_crops(real_graph, tmp_path) -> None:
    receipt, projection, binding, graph = real_graph
    output = PROJECT_ROOT / "output" / f"unit-shb-numeric-{tmp_path.name}"
    registry = build_semantic_graph_numeric_cell_crop_registry_v1(
        PROJECT_ROOT,
        output,
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    try:
        loaded, samples, registry_path = load_reference_blind_numeric_request(
            PROJECT_ROOT, output / "crop_registry.json"
        )
        assert loaded == registry
        assert registry_path == output / "crop_registry.json"
        assert registry["metrics"] == {
            "page_count": 1,
            "row_count": 4,
            "cell_count": 8,
            "primary_observation_counts": {"VALUE": 8},
        }
        assert registry["semantic_graph"]["graph_id"] == (
            "slagv2:graph:47ec2635a8b57ee0773f26612d97dc7ce1a700993b169c25d7286f9b74be28d7"
        )
        assert [cell["cell_id"] for cell in registry["cells"]] == [
            "page-0001-row-000-axis-1",
            "page-0001-row-000-axis-2",
            "page-0001-row-001-axis-1",
            "page-0001-row-001-axis-2",
            "page-0001-row-002-axis-1",
            "page-0001-row-002-axis-2",
            "page-0001-row-003-axis-1",
            "page-0001-row-003-axis-2",
        ]
        assert [cell["source_line_index"] for cell in registry["cells"]] == [
            42,
            43,
            45,
            46,
            48,
            49,
            50,
            51,
        ]
        assert [cell["primary_value"] for cell in registry["cells"]] == [
            "225268906",
            "215455247",
            "162845429",
            "156575830",
            "271496634",
            "242830903",
            "659610969",
            "614861980",
        ]
        assert [cell["crop_sha256"] for cell in registry["cells"]] == [
            "9e60eb77a704db461489ab9114530e4b500c0f2d1386d46194edbc6f156d8800",
            "b606bbbf3edbb13684e05d9ee87e438731f5b0d917f7fd11919516638207e8c7",
            "9987728b0cf5065dc605b3a82df6ecf1aa9428f51457d095dd77433ab57619fc",
            "47a7efc31b79a8d5cfc650d6e3d8cec6629e5406605e25aead4927951af2c8c4",
            "961032c4b05367f7136316fd220cab355bee445a44d8162e276f563f01101d88",
            "255e928fc8801941447c8ff65a35b95b49efb4a0c74d471a8e9901f866ffc541",
            "03676531f9a0f6c8c89e3633fc990ea8f98eaebc85245f3d4082a1d0788fd05b",
            "60a392293687ffac5a0fee0e0e42b2f30186505426de56f2cdda0cb68688c967",
        ]
        assert len(samples) == 8
        assert all(set(sample) == {"cell_id", "crop_path", "crop_sha256"} for sample in samples)
        assert all("primary_value" not in sample for sample in samples)
        assert (
            validate_semantic_graph_numeric_cell_crop_registry_replay_v1(
                registry,
                output,
                PROJECT_ROOT,
                graph,
                projection,
                binding,
                receipt,
                LOAN_MATURITY_BUCKETS_SPEC_V1,
                SPECS,
            )
            == registry
        )
        forged = deepcopy(registry)
        forged["cells"][0]["primary_value"] = "999999999"
        with pytest.raises(ValueError, match="registry identity or shape drifted"):
            validate_semantic_graph_numeric_cell_crop_registry_replay_v1(
                forged,
                output,
                PROJECT_ROOT,
                graph,
                projection,
                binding,
                receipt,
                LOAN_MATURITY_BUCKETS_SPEC_V1,
                SPECS,
            )
    finally:
        import shutil

        shutil.rmtree(output, ignore_errors=True)
