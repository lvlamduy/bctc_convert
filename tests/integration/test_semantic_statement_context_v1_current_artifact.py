from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    build_semantic_statement_context_v1,
    validate_semantic_statement_context_replay_v1,
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


def _json(path: Path | str) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


@pytest.fixture(scope="module")
def real_shb():
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
    wanted = page["result_ref"]["sha256"]
    target = None
    for case in _json(TIER1)["cases"]:
        provenance = case["provenance_only_not_inference"]
        for candidate in provenance["page_inputs"]:
            reference = candidate["result_ref"]
            if reference is not None and reference["sha256"] == wanted:
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
    return receipt, projection, binding


def test_real_shb_page24_exact_heading_binds_tm_consolidated_continuation(real_shb) -> None:
    receipt, projection, binding = real_shb
    context = build_semantic_statement_context_v1(projection, binding, receipt)

    assert (
        validate_semantic_statement_context_replay_v1(context, projection, binding, receipt)
        == context
    )
    assert context["status"] == "RESOLVED_VISIBLE_PAGE_STATEMENT_CONTEXT"
    assert context["statement_type"] == "TM"
    assert context["report_scope"] == "CONSOLIDATED"
    assert context["continuation"] is True
    assert context["heading_evidence"]["sample_id"] == "page-0001-line-0001"
    assert context["context_id"] == (
        "sscxtv1:context:a2d480f3bece8e0a29e0a935dbd4be00e4168159a6ec7d3d2946ab17d0b0ab8e"
    )
    assert context["source_local_page_id"] == (
        "ssv2:page:736b745df05b5c1f0ef81a5e985e38a44ef9b92612e9574c1b87ebb3e3b21ca1"
    )
    assert context["source_projection_sha256"] == (
        "1036a24b4fbf8dde6f6b20341cee6d640f7c12cc22d83f67a798af2152e06ff7"
    )
    assert context["semantic_page_binding_sha256"] == (
        "e89153d4d78d337e438b90157ea330e8a84890f58847615ed34e304eff2a3a52"
    )
    assert context["heading_evidence"]["raw_transformer_text_utf8"] == (
        "THUYẾT MINH BÁO CÁO TÀI CHÍNH HỢP NHẤT (TIẾP THEO)"
    )
    assert context["heading_evidence"]["crop_ref"]["sha256"] == (
        "c92d9a8a0093bf06c3fb8f41d96a216f106641a171e6858b5ffbc5126e145b2c"
    )
    assert context["heading_evidence"]["source_bbox_raw_pixels"] == [292, 124, 928, 164]
    assert context["readiness"]["schema_mapping_ready"] is False
    assert context["readiness"]["export_eligible"] is False
