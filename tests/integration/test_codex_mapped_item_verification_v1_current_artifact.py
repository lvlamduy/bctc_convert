from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from bctc_ai.mapping.codex_mapped_item_verification_v1 import (
    assemble_codex_mapped_item_verification_v1,
    authenticate_codex_mapped_item_review_v1,
    build_codex_mapped_item_verification_request_v1,
    validate_codex_mapped_item_verification_replay_v1,
    validate_codex_mapped_item_verification_request_replay_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    build_semantic_local_accounting_schema_candidate_v1,
)
from bctc_ai.source_structure.contracts_v1 import canonical_json_sha256_v1
from bctc_ai.source_structure.evidence_projection_v2 import project_authenticated_page_v2
from bctc_ai.source_structure.local_accounting_graph_v1 import (
    LOAN_MATURITY_BUCKETS_SPEC_V1,
    LOAN_QUALITY_CLASSIFICATION_SPEC_V1,
)
from bctc_ai.source_structure.semantic_local_accounting_graph_v2 import (
    build_semantic_local_accounting_graph_v2,
)
from bctc_ai.source_structure.semantic_statement_context_v1 import (
    build_semantic_statement_context_v1,
)
from bctc_ai.source_structure.vietocr_semantic_receipt_v2 import (
    bind_vietocr_semantic_page_v2,
    validate_vietocr_semantic_receipt_v2,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUN_ROOT = Path("output/development/vietocr-multibank-family-ocr-benchmark-v1/frozen-run")
MANIFEST = RUN_ROOT / "frozen/crop_manifest.json"
READER_REQUEST = RUN_ROOT / "frozen/reader_request.json"
RESULT = RUN_ROOT / "outputs/vgg-transformer/ocr_result.json"
RUN = RUN_ROOT / "outputs/vgg-transformer/run_manifest.json"
RESULT_SHA256 = "4277307a95738975bb720f3d5cff19b4e432e741a5052002efffcac5343197d1"
RUN_SHA256 = "6e7d3a9038ba2af6c449eff4f5bfe88df6380c02b9d378f49df21b7876ab5db7"
DOCUMENT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/documents/"
    "3a66122194e4dd2e0ca18d584beeacb81279cf71e276eface59d17e72813dcfd.json"
)
PAGE_RESULT = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/"
    "f6/f66ec66cf70b85c07c877881daf7d207dec7b754efbcafc1c88507962b77a82b.json"
)
SOURCE_PDF = Path("vietstock_bctc/SHB/2026/BCTC Hợp nhất quý 2 năm 2026.pdf")
RENDER = Path(
    "output/development/bank-corpus-wave-1-role-b-page-reader-v1/full-v3/objects/sha256/"
    "43/43067bf4cb05b4ea8c7b526111bc170a3ef969f7aa79fd59a4f036201947772e.png"
)
NUMERIC = Path("docs/experiments/E-0042-shb-maturity-numeric-verification.json")
SPECS = (LOAN_QUALITY_CLASSIFICATION_SPEC_V1, LOAN_MATURITY_BUCKETS_SPEC_V1)


def _json(path: Path) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


@pytest.fixture(scope="module")
def real_shb_inputs():
    required = (MANIFEST, READER_REQUEST, RESULT, RUN, DOCUMENT, PAGE_RESULT, SOURCE_PDF, RENDER)
    if not all((PROJECT_ROOT / path).is_file() for path in required):
        pytest.skip("exact SHB Transformer/source artifacts are not hydrated")
    receipt = validate_vietocr_semantic_receipt_v2(
        PROJECT_ROOT,
        MANIFEST,
        READER_REQUEST,
        RESULT,
        RUN,
        expected_ocr_result_sha256=RESULT_SHA256,
        expected_run_manifest_sha256=RUN_SHA256,
    )
    document = _json(DOCUMENT)
    projection = project_authenticated_page_v2(
        page_record=document["page_records"][23],
        page_result=_json(PAGE_RESULT),
    )
    binding = bind_vietocr_semantic_page_v2(projection, receipt)
    graph = build_semantic_local_accounting_graph_v2(
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    candidate = build_semantic_local_accounting_schema_candidate_v1(
        PROJECT_ROOT,
        graph,
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
    )
    context = build_semantic_statement_context_v1(projection, binding, receipt)
    return receipt, projection, binding, graph, candidate, context


def _request(real_shb_inputs):
    receipt, projection, binding, graph, candidate, context = real_shb_inputs
    return build_codex_mapped_item_verification_request_v1(
        PROJECT_ROOT,
        graph,
        candidate,
        context,
        (PROJECT_ROOT / NUMERIC).read_bytes(),
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
        source_pdf_path=SOURCE_PDF,
        target_page_render_path=RENDER,
    )


def test_exact_shb_request_replays_and_public_pinned_review_authenticates(real_shb_inputs):
    request, request_receipt = _request(real_shb_inputs)
    receipt, projection, binding, graph, candidate, context = real_shb_inputs
    replayed, replay_receipt = validate_codex_mapped_item_verification_request_replay_v1(
        request,
        PROJECT_ROOT,
        graph,
        candidate,
        context,
        (PROJECT_ROOT / NUMERIC).read_bytes(),
        projection,
        binding,
        receipt,
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
        source_pdf_path=SOURCE_PDF,
        target_page_render_path=RENDER,
    )
    assert replayed == request
    assert request["request_id"] == (
        "cimvrqv1:request:db05d26076a0ea1845d1da914d902415074be8334f3934eab3576e726ce1324e"
    )
    review, review_receipt = authenticate_codex_mapped_item_review_v1(PROJECT_ROOT, replay_receipt)
    assert review["review_id"] == (
        "codexmirv1:review:8e1f41013a9d950f70f57abb9f2166585eca75659de1735dc0dd0cb7684f43b1"
    )
    # Both independently minted request receipts bind the same exact immutable request bytes.
    review_again, _ = authenticate_codex_mapped_item_review_v1(PROJECT_ROOT, request_receipt)
    assert review_again == review


def test_exact_shb_golden_verdicts_keep_total_and_neighbours_out_of_mapping(real_shb_inputs):
    request, request_receipt = _request(real_shb_inputs)
    _review, review_receipt = authenticate_codex_mapped_item_review_v1(
        PROJECT_ROOT, request_receipt
    )
    result = assemble_codex_mapped_item_verification_v1(request_receipt, review_receipt)
    assert (
        validate_codex_mapped_item_verification_replay_v1(result, request_receipt, review_receipt)
        == result
    )
    assert result["input_identities"] == {
        "semantic_graph": request["input_identities"]["semantic_graph"],
        "schema_candidate": request["input_identities"]["schema_candidate"],
        "statement_context": request["input_identities"]["statement_context"],
        "source_projection_sha256": request["source_authority"]["source_projection_sha256"],
        "semantic_page_binding_sha256": request["input_identities"]["semantic_page_binding_sha256"],
        "numeric_verification": request["input_identities"]["numeric_verification"],
    }
    assert result["verification_id"] == (
        "codexmiv1:verification:d127ca7b4692a275dcb64af03df9e134870475c57979f8915847b73d3a7f71fd"
    )
    assert [
        (item["typed_role"], item["report_norm_id"], item["status"])
        for item in result["item_verdicts"]
    ] == [
        ("SHORT_TERM", 753, "VERIFIED_BY_CODEX"),
        ("MEDIUM_TERM", 754, "VERIFIED_BY_CODEX"),
        ("LONG_TERM", 755, "VERIFIED_BY_CODEX"),
        ("TOTAL", None, "VERIFIED_BY_CODEX"),
    ]
    assert [
        [value["normalized_decimal"] for value in item["values"]]
        for item in result["item_verdicts"]
    ] == [
        ["225268906", "215455247"],
        ["162845429", "156575830"],
        ["271496634", "242830903"],
        ["659610969", "614861980"],
    ]
    assert result["item_verdicts"][-1]["authority"] == {
        "accepted_mapping_for_exact_bound_source_observation": False,
        "source_value_readback": True,
        "source_total_readback_and_local_closure": True,
        "canonicalization": False,
        "value_materialization": False,
        "export": False,
        "production": False,
    }
    assert result["near_neighbour_verdicts"] == [
        {
            "report_norm_id": 5747,
            "status": "UNRESOLVED",
            "disposition": "NOT_OBSERVED_IN_BOUND_SOURCE_TABLE",
            "whole_document_absence_claim": False,
            "evidence_refs": [request["request_id"]],
        },
        {
            "report_norm_id": 1944,
            "status": "UNRESOLVED",
            "disposition": "SCHEMA_CONTEXT_UNRESOLVED_ORPHAN_MAPPING_INELIGIBLE",
            "whole_document_absence_claim": False,
            "evidence_refs": [request["request_id"]],
        },
    ]
    assert result["metrics"] == {
        "verified_mapped_row_count": 3,
        "verified_source_only_validation_count": 1,
        "unresolved_item_count": 0,
        "unresolved_near_neighbour_count": 2,
    }

    coordinated_tamper = copy.deepcopy(result)
    coordinated_tamper["input_identities"]["semantic_graph"]["graph_id"] = (
        f"slagv2:graph:{'0' * 64}"
    )
    coordinated_tamper.pop("verification_id")
    coordinated_tamper["verification_id"] = "codexmiv1:verification:" + canonical_json_sha256_v1(
        coordinated_tamper
    )
    with pytest.raises(ValueError, match="does not replay exactly"):
        validate_codex_mapped_item_verification_replay_v1(
            coordinated_tamper, request_receipt, review_receipt
        )
