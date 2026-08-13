from __future__ import annotations

import json
from pathlib import Path

import pytest

from bctc_ai.evaluation.family_sweep_contract_v1 import (
    BANK_PANEL_V1,
    _project_replayed_mapping,
    _replay_independent_mapping,
    _require_current_mapping_input_identities,
    _validate_independent_mapping,
    build_family_sweep_manifest_v1,
)
from bctc_ai.evaluation.loan_maturity_8bank_panel_prerequisite_v1 import (
    project_authenticated_loan_maturity_8bank_panel_selection_v1,
    replay_loan_maturity_8bank_panel_prerequisite_v1,
)
from bctc_ai.mapping.codex_mapped_item_verification_v1 import (
    assemble_codex_mapped_item_verification_v1,
    authenticate_codex_mapped_item_review_v1,
    build_codex_mapped_item_verification_request_v1,
)
from bctc_ai.mapping.semantic_local_accounting_schema_candidate_v1 import (
    build_semantic_local_accounting_schema_candidate_v1,
)
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
E0044 = Path("docs/experiments/E-0044-loan-maturity-8bank-vietocr-panel-prerequisite.json")


def _json(path: Path) -> dict:
    return json.loads((PROJECT_ROOT / path).read_bytes())


def test_real_e0044_capability_binds_manifest_bank_source_and_page_selection() -> None:
    panel, capability = replay_loan_maturity_8bank_panel_prerequisite_v1(PROJECT_ROOT, E0044)
    selection = project_authenticated_loan_maturity_8bank_panel_selection_v1(capability)
    source_sizes: dict[str, int] = {}
    for slot in panel["slots"]:
        result = _json(Path(slot["inventory_evidence"]["result_ref"]["path"]))
        source_sizes[slot["bank_code"]] = result["source_size_bytes"]
    plans = {
        bank: [
            {
                "trial_id": f"trial-{ordinal:04d}",
                "source_size_bytes": source_sizes[bank],
                "source_local_page_id": "ssv2:page:" + f"{ordinal:x}" * 64,
            }
        ]
        for ordinal, bank in enumerate(BANK_PANEL_V1, start=1)
    }

    manifest = build_family_sweep_manifest_v1(
        LOAN_MATURITY_BUCKETS_SPEC_V1,
        SPECS,
        plans,
        panel_selection_authority=capability,
    )

    assert manifest["panel_selection_authority"] == selection
    assert [
        (entry["bank"], entry["trials"][0]["source_sha256"], entry["trials"][0]["physical_page"])
        for entry in manifest["banks"]
    ] == [
        (slot["bank_code"], slot["source_pdf_sha256"], slot["physical_page"])
        for slot in selection["slots"]
    ]


def test_real_shb_calibration_verifier_projects_three_mappings_and_source_only_total() -> None:
    """Exercise the real verifier adapter without fabricating an eight-bank slot.

    SHB is the frozen mapped-item calibration authority but is deliberately not
    one of the fixed ACB/MBB/VPB/HDB/VCB/CTG/BID/VIB sweep slots.
    """

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
    _request, request_receipt = build_codex_mapped_item_verification_request_v1(
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
    _review, review_receipt = authenticate_codex_mapped_item_review_v1(
        PROJECT_ROOT, request_receipt
    )
    verification = assemble_codex_mapped_item_verification_v1(request_receipt, review_receipt)
    replayed = _replay_independent_mapping(verification, request_receipt, review_receipt)
    _require_current_mapping_input_identities(
        replayed,
        graph=graph,
        candidate=candidate,
        context=context,
        source_projection=projection,
        semantic_page_binding=binding,
    )
    mapping, numeric = _project_replayed_mapping(replayed, graph, candidate)
    candidate_projection = {
        "candidate_set_id": candidate["candidate_set_id"],
        "artifact_sha256": "a" * 64,
        "status": candidate["status"],
        "candidate_role_count": candidate["metrics"]["candidate_role_count"],
    }
    graph_projection = {
        "graph_id": graph["graph_id"],
        "artifact_sha256": "b" * 64,
        "status": graph["status"],
        "accepted_counts": graph["metrics"]["accepted_counts"],
        "unresolved_reasons": graph["unresolved_reasons"],
    }

    _validated, mapped, source_only, unresolved, near_neighbors = _validate_independent_mapping(
        mapping,
        accepted=True,
        candidate=candidate_projection,
        graph=graph_projection,
    )
    assert (mapped, source_only, unresolved, near_neighbors) == (3, 1, 0, 2)
    assert numeric["status"] == "VERIFIED"
    assert numeric["verified_cell_count"] == 8
    total = mapping["rows"][-1]
    assert total["typed_role"] == "TOTAL"
    assert total["candidate_report_norm_id"] is None
    assert total["verified_report_norm_id"] is None
    assert total["source_only_total"] is True
