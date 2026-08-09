from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from bctc_ai.core.hashing import sha256_bytes, sha256_file
from bctc_ai.corpus import wave1_pre_ocr_structure as pre_ocr_structure
from bctc_ai.corpus.bank_survey import (
    POLICY_RELATIVE_PATH,
    BankCorpusSurveyError,
    _classify_source_route,
    _filename_metadata,
    build_bank_corpus_inventory,
    build_wave_one_source_profile,
    publish_bank_corpus_inventory,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    _DOCUMENT_FEATURE_SUMMARY_FIELDS,
    _PAGE_FEATURE_FINGERPRINT_FIELDS,
    WaveOnePreOCRStructureError,
    _document_feature_fingerprint_sha256,
    _load_bound_published_json,
    _page_feature_fingerprint_sha256,
    build_wave_one_pre_ocr_structure_features,
    load_wave_one_pre_ocr_structure_policy,
    publish_wave_one_pre_ocr_structure_features,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    IMPLEMENTATION_RELATIVE_PATH as PRE_OCR_IMPLEMENTATION_RELATIVE_PATH,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    OUTPUT_RELATIVE_PATH as PRE_OCR_OUTPUT_RELATIVE_PATH,
)
from bctc_ai.corpus.wave1_pre_ocr_structure import (
    POLICY_RELATIVE_PATH as PRE_OCR_POLICY_RELATIVE_PATH,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
HYDRATED_WAVE_ONE_SENTINEL = (
    PROJECT_ROOT / "vietstock_bctc/ABB/2026/"
    "phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf"
)


@pytest.fixture(scope="module")
def hydrated_pre_ocr_structure_payload() -> dict[str, object]:
    if not HYDRATED_WAVE_ONE_SENTINEL.is_file():
        pytest.skip("Wave 1 PDFs are deliberately offloaded in lean checkouts")
    return build_wave_one_pre_ocr_structure_features(
        PROJECT_ROOT, PROJECT_ROOT / PRE_OCR_POLICY_RELATIVE_PATH
    )


def test_real_registered_inventory_is_complete_and_wave_one_is_bank_wide() -> None:
    payload = build_bank_corpus_inventory(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)
    accounting = payload["accounting"]
    selection = payload["wave_1"]

    assert accounting["registered_bank_count"] == 27
    assert accounting["registered_pdf_path_count"] == 2_567
    assert accounting["unique_pdf_content_count"] == 2_435
    assert accounting["duplicate_content_group_count"] == 132
    assert accounting["duplicate_extra_path_count"] == 132
    assert accounting["registered_pdf_bytes"] == 17_761_344_114
    assert selection["selected_bank_count"] == 27
    assert selection["selected_document_count"] == 27
    assert len({record["bank"] for record in selection["selected_documents"]}) == 27
    assert all(
        record["selection_status"] == "SELECTED_PENDING_SOURCE_SURVEY"
        and record["source_type_used_for_selection"] is False
        and record["dataset_role"] != "UNTOUCHED_HOLDOUT"
        for record in selection["selected_documents"]
    )
    assert accounting["filename_metadata_authoritative"] is False
    assert accounting["source_type_assessment_status"] == "PENDING_PDF_INSPECTION"


def test_wave_one_prefers_target_period_but_records_fallbacks() -> None:
    payload = build_bank_corpus_inventory(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)
    selected = {record["bank"]: record for record in payload["wave_1"]["selected_documents"]}

    projection = [
        {
            key: record[key]
            for key in ("bank", "document_id", "sha256", "size_bytes", "relative_path")
        }
        for record in payload["wave_1"]["selected_documents"]
    ]
    projection_bytes = (
        json.dumps(projection, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    assert sha256_bytes(projection_bytes) == (
        "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"
    )
    assert payload["wave_1"]["selection_receipt_sha256"] == sha256_bytes(projection_bytes)
    assert payload["wave_1"]["selection_receipt_size_bytes"] == 7_665
    assert payload["wave_1"]["selected_document_bytes"] == 248_588_591
    assert payload["wave_1"]["selection_rationale_counts"] == {
        "FALLBACK_Q2_2026_SCOPE_UNKNOWN": 2,
        "FALLBACK_Q2_2026_SEPARATE_SCOPE": 1,
        "PRIMARY_COMPARABLE_VI_Q2_2026_CONSOLIDATED": 23,
        "REUSED_REGISTERED_DEVELOPMENT_EVIDENCE_AFTER_METADATA_TIE": 1,
    }
    assert payload["wave_1"]["selected_dataset_role_counts"] == {
        "CALIBRATION": 2,
        "LOGIC_DEVELOPMENT": 1,
        "UNASSIGNED": 24,
    }
    assert payload["wave_1"]["filename_derived_counts"] == {
        "document_kind": {
            "FULL_FINANCIAL_STATEMENT_CANDIDATE": 27,
            "SUPPORTING_OR_PARTIAL_DOCUMENT": 0,
            "UNCLASSIFIED_DOCUMENT_KIND": 0,
        },
        "scope_hint": {
            "CONSOLIDATED": 24,
            "SEPARATE": 1,
            "UNKNOWN": 2,
            "AMBIGUOUS": 0,
        },
        "reporting_period_hint": {
            "ANNUAL": 0,
            "H1": 0,
            "Q1": 0,
            "Q2": 26,
            "Q3": 0,
            "Q4": 0,
            "UNKNOWN": 1,
            "AMBIGUOUS": 0,
        },
        "assurance_hint": {
            "AUDITED": 0,
            "REVIEWED": 0,
            "UNAUDITED": 0,
            "UNKNOWN": 27,
            "AMBIGUOUS": 0,
        },
        "language_hint": {
            "VI": 27,
            "EN": 0,
            "BILINGUAL_OR_AMBIGUOUS": 0,
            "UNKNOWN": 0,
        },
        "source_type_hint": {
            "SEARCHABLE_FILENAME_HINT": 1,
            "UNASSESSED_REQUIRES_PDF_INSPECTION": 26,
        },
    }

    assert selected["MBB"]["filename_metadata"]["reporting_period_hint"] == "Q2"
    assert selected["MBB"]["filename_metadata"]["scope_hint"] == "CONSOLIDATED"
    # The preserved VPB filename does not encode a quarter. Source inspection may
    # later establish Q1, but the metadata inventory must not infer it from prior work.
    assert selected["VPB"]["filename_metadata"]["reporting_period_hint"] == "UNKNOWN"
    assert selected["VPB"]["preferred_variant_matched"]["period"] is False
    assert selected["ABB"]["filename_metadata"]["scope_hint"] == "SEPARATE"
    assert selected["ABB"]["preferred_variant_matched"]["scope"] is False
    assert selected["LPB"]["filename_metadata"]["scope_hint"] == "UNKNOWN"
    assert selected["PGB"]["filename_metadata"]["scope_hint"] == "UNKNOWN"
    assert selected["SGB"]["relative_path"].endswith(
        "5_sgb_2026_7_27_989deeb_vi__bao_cao_tai_chinh_hop_nhat_q22026_daky.pdf"
    )


def test_filename_metadata_is_conservative_for_compact_and_vietnamese_forms() -> None:
    h1 = _filename_metadata(
        "vietstock_bctc/AAA/2026/BCTC Hợp nhất Soát xét 6 tháng đầu năm 2026.pdf",
        2026,
    )
    supporting = _filename_metadata(
        "vietstock_bctc/AAA/2026/2_vi_giaitrinhlienquandenbctc_q2_2026.pdf",
        2026,
    )
    unaudited = _filename_metadata(
        "vietstock_bctc/AAA/2026/BCTC hopnhat Q2 2026 chua kiem toan.pdf",
        2026,
    )

    assert h1["reporting_period_hint"] == "H1"
    assert h1["assurance_hint"] == "REVIEWED"
    assert supporting["document_kind"] == "SUPPORTING_OR_PARTIAL_DOCUMENT"
    assert unaudited["scope_hint"] == "CONSOLIDATED"
    assert unaudited["assurance_hint"] == "UNAUDITED"


def test_source_route_profile_is_page_evidence_driven() -> None:
    cases = (
        ((0, 0, 10, 10), "SCAN_ROUTE"),
        ((2, 2, 10, 10), "MIXED_PAGE_HYBRID_ROUTE"),
        (
            (10, 0, 10, 10),
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION",
        ),
        ((10, 10, 1, 0), "NATIVE_SEARCHABLE_ROUTE"),
        ((0, 0, 0, 0), "UNRESOLVED_SOURCE_ROUTE"),
    )
    for counts, expected in cases:
        assert (
            _classify_source_route(
                page_count=10,
                substantive_extracted_text_pages=counts[0],
                substantive_nonzero_alpha_text_pages=counts[1],
                displayed_image_pages=counts[2],
                dominant_raster_pages=counts[3],
            )
            == expected
        )
    with pytest.raises(BankCorpusSurveyError, match="page-evidence"):
        _classify_source_route(
            page_count=10,
            substantive_extracted_text_pages=11,
            substantive_nonzero_alpha_text_pages=0,
            displayed_image_pages=0,
            dominant_raster_pages=0,
        )


@pytest.mark.skipif(
    not (
        PROJECT_ROOT / "vietstock_bctc/ABB/2026/"
        "phpnchaip-bao-cao-tai-chinh-rieng-le-quy-ii-nam-2026-6a5df290b2d0a.pdf"
    ).is_file(),
    reason="Wave 1 PDFs are deliberately offloaded in lean checkouts",
)
def test_hydrated_wave_one_source_profile_has_exact_page_accounting() -> None:
    payload = build_wave_one_source_profile(PROJECT_ROOT, PROJECT_ROOT / POLICY_RELATIVE_PATH)

    assert payload["accounting"] == {
        "selected_document_count": 27,
        "source_profiled_document_count": 27,
        "structurally_surveyed_document_count": 0,
        "source_accounted_statement_block_count": 0,
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "total_pdf_page_count": 1_449,
        "any_extractable_text_layer_page_count": 156,
        "substantive_extractable_text_layer_page_count": 156,
        "substantive_nonzero_alpha_text_layer_page_count": 111,
        "substantive_zero_alpha_text_layer_page_count": 46,
        "displayed_image_page_count": 1_363,
        "dominant_displayed_raster_page_count": 1_356,
        "no_extracted_text_or_displayed_image_page_count": 0,
        "source_route_counts": {
            "SCAN_ROUTE": 11,
            "MIXED_PAGE_HYBRID_ROUTE": 14,
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION": 1,
            "NATIVE_SEARCHABLE_ROUTE": 1,
            "UNRESOLVED_SOURCE_ROUTE": 0,
        },
        "source_route_page_quadrant_counts": {
            "TEXT_LAYER_AND_DOMINANT_RASTER": 63,
            "TEXT_LAYER_AND_NONDOMINANT_RASTER": 93,
            "NO_TEXT_LAYER_AND_DOMINANT_RASTER": 1_293,
            "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER": 0,
        },
        "ocr_executed": False,
        "schema_used": False,
        "canonical_mapping_attempted": False,
    }
    profiles = {profile["bank"]: profile for profile in payload["profiles"]}
    assert profiles["HDB"]["source_route_recommendation"] == (
        "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION"
    )
    assert profiles["HDB"]["substantive_zero_alpha_text_layer_page_count"] == 44
    assert profiles["HDB"]["dominant_displayed_raster_page_count"] == 44
    assert profiles["MSB"]["displayed_image_page_count"] == 57
    assert profiles["VBB"]["substantive_extractable_text_layer_page_count"] == 2
    assert profiles["VBB"]["substantive_nonzero_alpha_text_layer_page_count"] == 1
    assert profiles["VPB"]["source_route_recommendation"] == "NATIVE_SEARCHABLE_ROUTE"
    assert profiles["VPB"]["substantive_nonzero_alpha_text_layer_page_count"] == 91
    assert profiles["VPB"]["dominant_displayed_raster_page_count"] == 0


def test_policy_rejects_source_type_or_schema_routing(tmp_path: Path) -> None:
    project = tmp_path / "project"
    (project / POLICY_RELATIVE_PATH.parent).mkdir(parents=True)
    policy = yaml.safe_load((PROJECT_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    policy["wave_1"]["source_type_used_for_selection"] = True
    (project / POLICY_RELATIVE_PATH).write_text(
        yaml.safe_dump(policy, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )

    with pytest.raises(BankCorpusSurveyError, match="selection gates"):
        build_bank_corpus_inventory(project, project / POLICY_RELATIVE_PATH)


def test_dataset_role_must_bind_an_exact_registered_source_path(tmp_path: Path) -> None:
    root = tmp_path / "project"
    fixture_paths = (
        POLICY_RELATIVE_PATH,
        Path("data/registered/bank_registry.json"),
        Path("data/registered/source_registry.jsonl"),
        Path("data/registered/dataset_roles.jsonl"),
        Path("src/bctc_ai/corpus/bank_survey.py"),
    )
    for relative in fixture_paths:
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes((PROJECT_ROOT / relative).read_bytes())
    role_path = root / "data/registered/dataset_roles.jsonl"
    records = [json.loads(line) for line in role_path.read_text(encoding="utf-8").splitlines()]
    records[0]["source_path"] = records[1]["source_path"]
    role_path.write_text(
        "".join(
            json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n" for record in records
        ),
        encoding="utf-8",
    )

    with pytest.raises(BankCorpusSurveyError, match="malformed record"):
        build_bank_corpus_inventory(root, root / POLICY_RELATIVE_PATH)


def test_publication_is_canonical_and_exclusive(tmp_path: Path) -> None:
    root = tmp_path / "project"
    for relative in (
        POLICY_RELATIVE_PATH,
        Path("data/registered/bank_registry.json"),
        Path("data/registered/source_registry.jsonl"),
        Path("data/registered/dataset_roles.jsonl"),
        Path("src/bctc_ai/corpus/bank_survey.py"),
    ):
        source = PROJECT_ROOT / relative
        target = root / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(source.read_bytes())
    output = root / "output/development/bank-corpus-survey-v1/corpus-inventory.json"
    path, digest, size = publish_bank_corpus_inventory(root, output_path=output)
    encoded = path.read_bytes()
    payload = json.loads(encoded)

    assert digest == sha256_bytes(encoded)
    assert size == len(encoded)
    assert encoded == (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with pytest.raises(BankCorpusSurveyError, match="already exists"):
        publish_bank_corpus_inventory(root, output_path=output)


def test_historical_survey_policy_and_producer_remain_byte_exact() -> None:
    assert sha256_file(PROJECT_ROOT / POLICY_RELATIVE_PATH) == (
        "e72adacf9ba664f9dc39398c3d09339ca753ee0d8477d1903a4263fb0ccd7467"
    )
    assert sha256_file(PROJECT_ROOT / "src/bctc_ai/corpus/bank_survey.py") == (
        "5fb234227c6a8a1c970c89c12e8f5139c29252134ce7c9f691bc9c4b1f46e15a"
    )


def test_pre_ocr_policy_is_a_separate_fixed_authority(tmp_path: Path) -> None:
    policy = load_wave_one_pre_ocr_structure_policy(
        PROJECT_ROOT / PRE_OCR_POLICY_RELATIVE_PATH, PROJECT_ROOT
    )
    assert policy["policy"] == "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_POLICY_V1"
    assert policy["upstream_binding"]["artifacts_rebuilt_by_this_run"] is False

    root = tmp_path / "project"
    target = root / PRE_OCR_POLICY_RELATIVE_PATH
    target.parent.mkdir(parents=True)
    target.write_bytes((PROJECT_ROOT / PRE_OCR_POLICY_RELATIVE_PATH).read_bytes())
    target.write_text(
        target.read_text(encoding="utf-8").replace("ocr_allowed: false", "ocr_allowed: true"),
        encoding="utf-8",
    )
    with pytest.raises(WaveOnePreOCRStructureError, match="policy bytes drifted"):
        load_wave_one_pre_ocr_structure_policy(target, root)


def test_pre_ocr_published_input_binding_fails_closed_on_byte_drift(
    tmp_path: Path,
) -> None:
    root = tmp_path / "project"
    relative_path = "output/upstream.json"
    source = root / relative_path
    source.parent.mkdir(parents=True)
    payload = {
        "format_version": "UPSTREAM_V1",
        "status": "COMPLETE",
        "claim_boundary": "EVIDENCE_ONLY",
    }
    encoded = (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode()
    source.write_bytes(encoded)
    specification = {
        "path": relative_path,
        "sha256": sha256_bytes(encoded),
        "size_bytes": len(encoded),
        **payload,
    }
    loaded, ledger = _load_bound_published_json(
        root,
        specification,
        label="synthetic published input",
        kind="SYNTHETIC",
    )
    assert loaded == payload
    assert ledger["binding_mode"] == "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY"

    source.write_bytes(encoded + b" ")
    with pytest.raises(WaveOnePreOCRStructureError, match="identity drifted"):
        _load_bound_published_json(
            root,
            specification,
            label="synthetic published input",
            kind="SYNTHETIC",
        )


def test_pre_ocr_feature_fingerprints_are_content_and_identity_bounded() -> None:
    contract_hash = "a" * 64
    page_features = {field: index for index, field in enumerate(_PAGE_FEATURE_FINGERPRINT_FIELDS)}
    page_fingerprint = _page_feature_fingerprint_sha256(page_features, contract_hash)
    identity_and_content_mutation = deepcopy(page_features)
    identity_and_content_mutation.update(
        {
            "bank": "SYNTHETIC_BANK",
            "relative_path": "somewhere/else.pdf",
            "document_id": "synthetic-document",
            "page_number": 999,
            "source_label_text": "A different source label",
            "form_code_text": "B01/TCTD",
            "financial_value_text": "123456789",
            "canonical_schema_id": 9999,
            "nonzero_alpha_text_layer_form_code_unique_normalized_token_count": 7,
        }
    )
    assert (
        _page_feature_fingerprint_sha256(identity_and_content_mutation, contract_hash)
        == page_fingerprint
    )
    structural_mutation = deepcopy(page_features)
    structural_mutation["effective_width_mpt"] += 1
    assert _page_feature_fingerprint_sha256(structural_mutation, contract_hash) != page_fingerprint

    summary = {field: index for index, field in enumerate(_DOCUMENT_FEATURE_SUMMARY_FIELDS)}
    run = [{"start_page": 1, "end_page": 1, "length": 1, "value": "X"}]
    document_fingerprint = _document_feature_fingerprint_sha256(
        summary=summary,
        page_feature_fingerprints=[page_fingerprint],
        orientation_runs=run,
        rotation_runs=run,
        geometry_family_runs=run,
        source_route_quadrant_runs=run,
        feature_contract_sha256=contract_hash,
    )
    summary_with_candidate_content = {
        **summary,
        "bank": "SYNTHETIC_BANK",
        "source_label_text": "A source label",
        "financial_value_text": "1000",
        "nonzero_alpha_text_layer_form_code_unique_normalized_token_occurrence_count": 3,
    }
    assert (
        _document_feature_fingerprint_sha256(
            summary=summary_with_candidate_content,
            page_feature_fingerprints=[page_fingerprint],
            orientation_runs=run,
            rotation_runs=run,
            geometry_family_runs=run,
            source_route_quadrant_runs=run,
            feature_contract_sha256=contract_hash,
        )
        == document_fingerprint
    )
    changed_summary = deepcopy(summary)
    changed_summary["page_count"] += 1
    assert (
        _document_feature_fingerprint_sha256(
            summary=changed_summary,
            page_feature_fingerprints=[page_fingerprint],
            orientation_runs=run,
            rotation_runs=run,
            geometry_family_runs=run,
            source_route_quadrant_runs=run,
            feature_contract_sha256=contract_hash,
        )
        != document_fingerprint
    )


def test_hydrated_pre_ocr_structure_has_exact_feature_accounting(
    hydrated_pre_ocr_structure_payload: dict[str, object],
) -> None:
    payload = hydrated_pre_ocr_structure_payload
    assert payload["status"] == ("COMPLETE_PRE_OCR_FEATURE_ACCOUNTING_STRUCTURE_SURVEY_PENDING")
    assert payload["claim_boundary"] == (
        "SELECTED_WAVE_1_PRE_OCR_PAGE_GEOMETRY_ROUTING_AND_FEATURE_CANDIDATES_ONLY"
    )
    assert payload["accounting"] == {
        "selected_document_count": 27,
        "pdf_hash_and_size_revalidated_document_count": 27,
        "source_profile_exactly_reconciled_document_count": 27,
        "pre_ocr_feature_profiled_document_count": 27,
        "total_pdf_page_count": 1_449,
        "page_geometry_accounted_count": 1_449,
        "page_source_route_quadrant_feature_accounted_count": 1_449,
        "text_layer_traversed_page_count": 1_449,
        "orientation_page_counts": {
            "PORTRAIT": 1_362,
            "LANDSCAPE": 87,
            "SQUARE": 0,
        },
        "rotation_page_counts": {"0": 1_175, "90": 3, "180": 0, "270": 271},
        "orientation_transition_count": 117,
        "rotation_transition_count": 31,
        "source_route_quadrant_transition_count": 21,
        "portrait_only_document_count": 12,
        "mixed_orientation_document_count": 15,
        "geometry_family_page_counts": {
            "A4_GEOMETRY_LIKE": 1_358,
            "LETTER_GEOMETRY_LIKE": 91,
            "OTHER_GEOMETRY": 0,
        },
        "geometry_family_document_counts": {
            "A4_GEOMETRY_LIKE": 26,
            "LETTER_GEOMETRY_LIKE": 1,
            "OTHER_GEOMETRY": 0,
        },
        "cropbox_difference_page_count": 0,
        "displayed_image_page_count": 1_363,
        "dominant_raster_page_count": 1_356,
        "effective_dpi_band_page_counts": {
            "75": 93,
            "100": 44,
            "125": 1,
            "150": 451,
            "200": 661,
            "300": 106,
        },
        "any_extractable_text_layer_page_count": 156,
        "substantive_extractable_text_page_count": 156,
        "substantive_nonzero_alpha_text_page_count": 111,
        "substantive_zero_alpha_text_page_count": 46,
        "no_extracted_text_or_displayed_image_page_count": 0,
        "source_route_candidate_counts": {
            "SCAN_ROUTE": 11,
            "MIXED_PAGE_HYBRID_ROUTE": 14,
            "SEARCHABLE_OVER_IMAGE_REQUIRES_GHOST_TEXT_VALIDATION": 1,
            "NATIVE_SEARCHABLE_ROUTE": 1,
            "UNRESOLVED_SOURCE_ROUTE": 0,
        },
        "source_route_quadrant_page_counts": {
            "TEXT_LAYER_AND_DOMINANT_RASTER": 63,
            "TEXT_LAYER_AND_NONDOMINANT_RASTER": 93,
            "NO_TEXT_LAYER_AND_DOMINANT_RASTER": 1_293,
            "NO_TEXT_LAYER_AND_NONDOMINANT_RASTER": 0,
        },
        "nonzero_alpha_text_layer_form_code_candidate_page_count": 89,
        "nonzero_alpha_text_layer_form_code_candidate_document_count": 2,
        "nonzero_alpha_text_layer_form_code_unique_normalized_token_occurrence_count": 89,
        "form_code_candidate_statement_classification_count": 0,
        "vector_drawing_page_count": 110,
        "vector_drawing_path_count": 1_922,
        "structurally_surveyed_document_count": 0,
        "statement_sequence_classified_document_count": 0,
        "source_accounted_statement_block_count": 0,
        "source_accounted_statement_page_count": 0,
        "statement_type_classified_page_count": 0,
        "accepted_title_candidate_count": 0,
        "accepted_table_count": 0,
        "source_accounted_table_count": 0,
        "source_accounted_logical_row_count": 0,
        "source_accounted_visible_row_count": 0,
        "source_accounted_visible_value_cell_count": 0,
        "source_accounted_period_axis_count": 0,
        "source_accounted_unit_axis_count": 0,
        "source_accounted_scope_count": 0,
        "source_accounted_hierarchy_relationship_count": 0,
        "render_visibility_validated_page_count": 0,
        "ocr_processed_page_count": 0,
        "financial_value_semantically_extracted_count": 0,
        "verbatim_financial_value_retained_count": 0,
        "absence_declaration_count": 0,
        "unresolved_statement_sequence_document_count": 27,
        "unresolved_statement_block_document_count": 27,
        "unresolved_table_topology_document_count": 27,
        "unresolved_period_axis_document_count": 27,
        "unresolved_unit_axis_document_count": 27,
        "unresolved_scope_document_count": 27,
        "unresolved_cash_flow_method_document_count": 27,
        "unresolved_notes_boundary_document_count": 27,
        "schema_used": False,
        "canonical_mapping_attempted": False,
        "role_a_used": False,
        "historical_values_used": False,
        "bank_specific_routing_used": False,
        "absence_claims_allowed": False,
    }


def test_hydrated_pre_ocr_structure_has_exact_canonical_bytes(
    hydrated_pre_ocr_structure_payload: dict[str, object],
) -> None:
    payload = hydrated_pre_ocr_structure_payload
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    assert len(encoded) == 3_730_164
    assert sha256_bytes(encoded) == (
        "9e4f8fe893e0f8967759eecf2647f4b9f921e97668c220e1237a6ce81059507c"
    )
    assert payload["implementation"]["sha256"] == (
        "12436a146e5545def0def96b25f9f07a18159e5318feabbddbff0bde67471266"
    )
    assert payload["authority"] == {
        "kind": "FIXED_WAVE_1_PRE_OCR_STRUCTURE_POLICY_V1",
        "path": PRE_OCR_POLICY_RELATIVE_PATH.as_posix(),
        "sha256": "112064f2395c2ef3fc2481631f86ea09fdd1f5328edd9d03c31893dcc8bd3069",
        "size_bytes": 6_065,
        "policy": "BANK_CORPUS_WAVE_1_PRE_OCR_STRUCTURE_FEATURES_POLICY_V1",
        "claim_boundary": (
            "SELECTED_WAVE_1_PRE_OCR_PAGE_GEOMETRY_ROUTING_AND_FEATURE_CANDIDATES_ONLY"
        ),
    }


def test_hydrated_pre_ocr_structure_binds_inputs_and_keeps_layer_boundaries(
    hydrated_pre_ocr_structure_payload: dict[str, object],
) -> None:
    payload = hydrated_pre_ocr_structure_payload
    assert payload["selection_receipt_sha256"] == (
        "832cea1bee22f0bb08c422490dd2afe4e23bc91c56cdee6db382b1bfdc744d28"
    )
    assert payload["upstream_artifacts_rebuilt_by_this_run"] is False
    assert [(record["sha256"], record["size_bytes"]) for record in payload["inputs"]] == [
        (
            "fff64ca4d25de646cd2f4661d99fc9623e6edc8c7c6b0cd321c0d2f9af9cebd8",
            2_181_864,
        ),
        (
            "28fb3485b9424e2052ae981942476e681d8fbdcbf1131467a1d65778a20cb19b",
            857_274,
        ),
    ]
    assert all(
        record["binding_mode"] == "EXACT_PUBLISHED_ARTIFACT_BYTES_READ_ONLY"
        and record["rebuilt_by_this_run"] is False
        and record["selection_receipt_sha256"] == payload["selection_receipt_sha256"]
        for record in payload["inputs"]
    )
    assert payload["authority"]["path"] == PRE_OCR_POLICY_RELATIVE_PATH.as_posix()
    assert payload["implementation"]["path"] == (PRE_OCR_IMPLEMENTATION_RELATIVE_PATH.as_posix())
    assert len(payload["source_pdf_ledger"]) == 27
    assert sum(record["page_count"] for record in payload["source_pdf_ledger"]) == 1_449
    assert all(
        record["hash_and_size_revalidation_status"] == "MATCH"
        and record["source_profile_reconciliation_status"] == "EXACT_PAGE_AND_DOCUMENT_REPLAY"
        and len(record["upstream_source_route_fingerprint_sha256"]) == 64
        for record in payload["source_pdf_ledger"]
    )
    assert payload["feature_fingerprints_are_canonical_accounting_identity"] is False
    assert payload["feature_fingerprints_are_canonical_mapping_authority"] is False

    documents = payload["documents"]
    assert len(documents) == 27
    assert sum(len(document["pages"]) for document in documents) == 1_449
    assert all(
        document["document_feature_fingerprint_is_canonical_accounting_identity"] is False
        and document["document_feature_fingerprint_is_canonical_mapping_authority"] is False
        and document["statement_sequence_status"] == "UNRESOLVED_PRE_OCR"
        and document["table_topology_status"] == "UNRESOLVED_PRE_OCR"
        and document["render_visibility_validation_status"] == "NOT_RUN"
        and document["ocr_status"] == "NOT_RUN"
        and sum(run["length"] for run in document["orientation_runs"]) == document["page_count"]
        and sum(run["length"] for run in document["rotation_runs"]) == document["page_count"]
        and sum(run["length"] for run in document["source_route_quadrant_feature_runs"])
        == document["page_count"]
        for document in documents
    )
    assert all(
        page["feature_fingerprint_is_canonical_accounting_identity"] is False
        and page["feature_fingerprint_is_canonical_mapping_authority"] is False
        and page["render_visibility_validation_status"] == "NOT_RUN"
        and page["ocr_status"] == "NOT_RUN"
        and page["statement_type_status"] == "UNRESOLVED_PRE_OCR"
        and page["table_status"] == "UNRESOLVED_PRE_OCR"
        and page["geometry_family_candidate_is_diagnostic_only"] is True
        for document in documents
        for page in document["pages"]
    )
    assert "NOT_OBSERVED" not in json.dumps(payload, ensure_ascii=False)


def test_hydrated_pre_ocr_form_codes_are_proxy_candidates_not_fingerprints(
    hydrated_pre_ocr_structure_payload: dict[str, object],
) -> None:
    payload = hydrated_pre_ocr_structure_payload
    candidate_documents = {
        document["bank"]: document
        for document in payload["documents"]
        if document["feature_summary"]["nonzero_alpha_text_layer_form_code_candidate_page_count"]
    }
    assert {
        bank: document["feature_summary"]["nonzero_alpha_text_layer_form_code_candidate_page_count"]
        for bank, document in candidate_documents.items()
    } == {"MBB": 2, "VPB": 87}
    assert all(
        record["status"] == "PROXY_UNVALIDATED_RENDER_VISIBILITY"
        and len(record["candidates"]) == len(set(record["candidates"]))
        for document in candidate_documents.values()
        for record in document["nonzero_alpha_text_layer_form_code_candidate_pages"]
    )
    assert (
        payload["form_code_candidate_counting_basis"]
        == "UNIQUE_NORMALIZED_TOKENS_PER_PAGE_SUMMED_ACROSS_PAGES"
    )
    assert (
        "nonzero_alpha_text_layer_form_code_unique_normalized_token_count"
        not in _PAGE_FEATURE_FINGERPRINT_FIELDS
    )


def test_pre_ocr_publication_is_canonical_and_exclusive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = tmp_path / "project"
    payload = {"format_version": "SYNTHETIC", "unicode": "đ", "z": 1}
    monkeypatch.setattr(
        pre_ocr_structure,
        "build_wave_one_pre_ocr_structure_features",
        lambda project_root, policy_path: payload,
    )
    output = root / PRE_OCR_OUTPUT_RELATIVE_PATH
    path, digest, size = publish_wave_one_pre_ocr_structure_features(root, output_path=output)
    encoded = path.read_bytes()
    assert digest == sha256_bytes(encoded)
    assert size == len(encoded)
    assert encoded == (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode("utf-8")
    with pytest.raises(WaveOnePreOCRStructureError, match="already exists"):
        publish_wave_one_pre_ocr_structure_features(root, output_path=output)
